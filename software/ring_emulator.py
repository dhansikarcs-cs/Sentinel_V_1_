"""
Ring BLE Emulator — simulates the Jointport ring's GATT service over Bluetooth
or a local TCP socket for development without hardware.

Usage:
  python ring_emulator.py [--mode tcp|ble] [--port 8888]

In TCP mode, connects to software/ring_.py via the RingDataSource interface.
In BLE mode, requires `bleak` library and a BLE adapter.
"""

import argparse
import json
import struct
import time
import socket
import threading
from datetime import datetime
from ring_ import (
    SensorData, IMUData, SimulatedRing, RingDataSource,
    encode_hr_notification, encode_ppg_sample, encode_imu_data,
    BLE_SERVICE_UUID, BLE_HR_UUID, BLE_PPG_UUID, BLE_IMU_UUID, BLE_TEMP_UUID, BLE_CMD_UUID,
)


class TCPRingEmulator:
    """Emulates ring via TCP socket — for local dev testing.

    Protocol: JSON lines over TCP.
    Client sends:  {"cmd": "read"} or {"cmd": "stream", "interval": 1.0}
    Server responds with SensorData as JSON.
    """

    def __init__(self, host="127.0.0.1", port=8888, intensity=1.0):
        self.host = host
        self.port = port
        self.intensity = intensity
        self.sim = SimulatedRing()
        self.sim.device_id = "emulator"
        self.server = None
        self.running = False

    def start(self):
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind((self.host, self.port))
        self.server.listen(5)
        self.server.settimeout(1.0)
        self.running = True
        print(f"[TCP Emulator] Listening on {self.host}:{self.port}")

        while self.running:
            try:
                conn, addr = self.server.accept()
                print(f"[TCP Emulator] Client connected: {addr}")
                threading.Thread(target=self._handle_client, args=(conn,), daemon=True).start()
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    print(f"[TCP Emulator] Error: {e}")

    def stop(self):
        self.running = False
        if self.server:
            self.server.close()

    def _handle_client(self, conn):
        buf = b""
        self._streaming = False
        self._stream_interval = 1.0
        try:
            while self.running:
                if self._streaming:
                    data = self.sim.read_sensors(self.intensity)
                    payload = json.dumps(data.to_dict()) + "\n"
                    try:
                        conn.sendall(payload.encode())
                    except Exception:
                        break
                    time.sleep(self._stream_interval)
                else:
                    try:
                        conn.settimeout(0.1)
                        chunk = conn.recv(4096)
                        if not chunk:
                            break
                        buf += chunk
                        while b"\n" in buf:
                            line, buf = buf.split(b"\n", 1)
                            try:
                                self._process_command(conn, line.decode("utf-8", errors="replace").strip())
                            except Exception:
                                pass
                    except socket.timeout:
                        continue
                    except Exception:
                        break
        finally:
            conn.close()

    def _process_command(self, conn, line):
        try:
            msg = json.loads(line)
            cmd = msg.get("cmd", "")
            if cmd == "read":
                data = self.sim.read_sensors(self.intensity)
                conn.sendall((json.dumps(data.to_dict()) + "\n").encode())
            elif cmd == "stream":
                self._streaming = True
                self._stream_interval = msg.get("interval", 1.0)
            elif cmd == "stop":
                self._streaming = False
            elif cmd == "ping":
                conn.sendall('{"status":"ok"}\n'.encode())
        except json.JSONDecodeError:
            pass


class BLERingEmulator:
    """Emulates ring via BLE GATT service — requires `bleak` library.

    Usage: python ring_emulator.py --mode ble
    """

    def __init__(self, intensity=1.0):
        self.intensity = intensity
        self.sim = SimulatedRing()
        self.sim.device_id = "ble-emulator"

    async def start(self):
        try:
            from bleak import BleakServer
        except ImportError:
            print("BLE mode requires bleak: pip install bleak")
            return

        print("[BLE Emulator] Starting BLE GATT server...")
        print(f"  Service UUID: {BLE_SERVICE_UUID}")
        print(f"  HR: {BLE_HR_UUID}")
        print(f"  PPG: {BLE_PPG_UUID}")
        print(f"  IMU: {BLE_IMU_UUID}")
        print(f"  Temp: {BLE_TEMP_UUID}")
        print(f"  CMD: {BLE_CMD_UUID}")

        async def hr_callback(characteristic, timeout=0):
            data = self.sim.read_sensors(self.intensity)
            return encode_hr_notification(data.bpm)

        async def ppg_callback(characteristic, timeout=0):
            import random
            sample = random.randint(-2048, 2047)
            return encode_ppg_sample(sample, 0)

        async def imu_callback(characteristic, timeout=0):
            data = self.sim.read_sensors(self.intensity)
            accel = (int(data.imu.accel_x * 1000), int(data.imu.accel_y * 1000), int(data.imu.accel_z * 1000))
            gyro = (int(data.imu.gyro_x * 1000), int(data.imu.gyro_y * 1000), int(data.imu.gyro_z * 1000))
            return encode_imu_data(accel, gyro)

        async def temp_callback(characteristic, timeout=0):
            data = self.sim.read_sensors(self.intensity)
            return struct.pack("<h", int(data.temperature * 100))

        async def cmd_callback(characteristic, value):
            cmd = decode_cmd_write(value)
            print(f"[BLE Emulator] Received CMD: {cmd}")

        server = BleakServer()
        service = await server.add_service(BLE_SERVICE_UUID)
        await service.add_characteristic(BLE_HR_UUID, hr_callback, notify=True)
        await service.add_characteristic(BLE_PPG_UUID, ppg_callback, notify=True)
        await service.add_characteristic(BLE_IMU_UUID, imu_callback, notify=True)
        await service.add_characteristic(BLE_TEMP_UUID, temp_callback, read=True)
        await service.add_characteristic(BLE_CMD_UUID, cmd_callback, write=True)

        await server.start()
        print("[BLE Emulator] Running. Press Ctrl+C to stop.")
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            pass
        finally:
            await server.stop()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ring BLE/TCP Emulator")
    parser.add_argument("--mode", choices=["tcp", "ble"], default="tcp")
    parser.add_argument("--port", type=int, default=8888)
    parser.add_argument("--intensity", type=float, default=1.0)
    args = parser.parse_args()

    if args.mode == "ble":
        import asyncio
        emu = BLERingEmulator(args.intensity)
        asyncio.run(emu.start())
    else:
        emu = TCPRingEmulator(port=args.port, intensity=args.intensity)
        try:
            emu.start()
        except KeyboardInterrupt:
            emu.stop()
            print("\n[TCP Emulator] Stopped.")