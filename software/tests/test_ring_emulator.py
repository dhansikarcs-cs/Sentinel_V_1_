import os
import sys
import json
import time
import socket
import struct
import threading

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from ring_emulator import TCPRingEmulator
from ring_ import (
    SensorData, decode_hr_notification, decode_imu_data,
    encode_hr_notification, encode_imu_data, encode_ppg_sample,
    decode_cmd_write,
)


def _read_line(sock, timeout=3.0):
    sock.settimeout(timeout)
    buf = b""
    while b"\n" not in buf:
        chunk = sock.recv(1)
        if not chunk:
            break
        buf += chunk
    line = buf.split(b"\n", 1)[0]
    return line.decode()


@pytest.fixture
def emulator():
    emu = TCPRingEmulator(port=0)
    emu.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    emu.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    emu.server.bind(("127.0.0.1", 0))
    emu.port = emu.server.getsockname()[1]
    emu.server.listen(5)
    emu.server.settimeout(1.0)
    emu.running = True

    def accept_loop():
        while emu.running:
            try:
                conn, addr = emu.server.accept()
                threading.Thread(target=emu._handle_client, args=(conn,), daemon=True).start()
            except socket.timeout:
                continue
            except Exception:
                if emu.running:
                    raise

    t = threading.Thread(target=accept_loop, daemon=True)
    t.start()
    yield emu
    emu.running = False
    emu.server.close()


@pytest.fixture
def client(emulator):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect(("127.0.0.1", emulator.port))
    yield sock
    sock.close()


class TestTCPEmulatorConnection:
    def test_ping(self, client):
        client.sendall(b'{"cmd":"ping"}\n')
        resp = _read_line(client)
        assert json.loads(resp) == {"status": "ok"}

    def test_read(self, client):
        client.sendall(b'{"cmd":"read"}\n')
        resp = json.loads(_read_line(client))
        assert "bpm" in resp
        assert "stress" in resp
        assert "mood" in resp
        assert 40 <= resp["bpm"] <= 120

    def test_stream_start_stop(self, client):
        client.sendall(b'{"cmd":"stream","interval":0.01}\n')
        time.sleep(0.05)
        for _ in range(10):
            try:
                client.settimeout(0.01)
                chunk = client.recv(4096)
                if not chunk:
                    break
            except socket.timeout:
                break
        client.sendall(b'{"cmd":"stop"}\n')
        time.sleep(0.02)


class TestTCPEmulatorFailureModes:
    def test_invalid_json_ignored(self, client):
        client.sendall(b'not json\n')
        time.sleep(0.1)
        client.sendall(b'{"cmd":"ping"}\n')
        resp = _read_line(client)
        assert json.loads(resp) == {"status": "ok"}

    def test_malformed_json_ignored(self, client):
        client.sendall(b'{"cmd": "read"\n')
        time.sleep(0.1)
        client.sendall(b'{"cmd":"ping"}\n')
        resp = _read_line(client)
        assert json.loads(resp) == {"status": "ok"}

    def test_unknown_command_ignored(self, client):
        client.sendall(b'{"cmd":"xyzzy"}\n')
        time.sleep(0.1)
        client.sendall(b'{"cmd":"ping"}\n')
        resp = _read_line(client)
        assert json.loads(resp) == {"status": "ok"}

    def test_garbage_binary_data(self, client):
        client.sendall(b"\x00\x01\x02\xff\xfe\xfd\x00\x00\x00\x00\x00\x00\n")
        time.sleep(0.1)
        client.sendall(b'{"cmd":"ping"}\n')
        resp = _read_line(client)
        assert json.loads(resp) == {"status": "ok"}

    def test_partial_tcp_split(self, client):
        client.sendall(b'{"cmd"')
        time.sleep(0.05)
        client.sendall(b':"ping"}\n')
        resp = _read_line(client)
        assert json.loads(resp) == {"status": "ok"}

    def test_empty_line_ignored(self, client):
        client.sendall(b"\n")
        time.sleep(0.05)
        client.sendall(b'{"cmd":"ping"}\n')
        resp = _read_line(client)
        assert json.loads(resp) == {"status": "ok"}

    def test_client_disconnect_early(self, emulator):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(("127.0.0.1", emulator.port))
        sock.close()
        time.sleep(0.1)
        assert emulator.running

    def test_many_clients(self, emulator):
        socks = []
        for _ in range(20):
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect(("127.0.0.1", emulator.port))
            socks.append(s)
        for s in socks:
            s.sendall(b'{"cmd":"ping"}\n')
            resp = _read_line(s)
            assert json.loads(resp) == {"status": "ok"}
        for s in socks:
            s.close()

    def test_large_payload_no_crash(self, client):
        big = json.dumps({"cmd": "read", "padding": "x" * 10000}) + "\n"
        client.sendall(big.encode())
        resp = json.loads(_read_line(client))
        assert "bpm" in resp

    def test_huge_data_no_crash(self, client):
        client.sendall(b"x" * 100000 + b"\n")
        time.sleep(0.1)
        client.sendall(b'{"cmd":"ping"}\n')
        resp = _read_line(client)
        assert json.loads(resp) == {"status": "ok"}


class TestProtocolVulnerability:
    def test_decode_cmd_write_ascii(self):
        assert decode_cmd_write(b"hello") == "hello"

    def test_decode_cmd_write_binary(self):
        result = decode_cmd_write(b"\x00\x01\x02\xff")
        assert isinstance(result, str)

    def test_decode_cmd_write_empty(self):
        assert decode_cmd_write(b"") == ""

    def test_hr_encoding_buffer_underflow(self):
        with pytest.raises((struct.error, IndexError)):
            decode_hr_notification(b"\x00")

    def test_imu_encoding_buffer_underflow(self):
        with pytest.raises((struct.error, IndexError)):
            decode_imu_data(b"\x00" * 4)

    def test_imu_encoding_buffer_overflow(self):
        data = encode_imu_data((0, 0, 0), (0, 0, 0))
        assert len(data) == 12
        decoded = decode_imu_data(data)
        assert decoded["accel_mg"] == (0, 0, 0)
        assert decoded["gyro_mdps"] == (0, 0, 0)

    def test_hr_values_edge(self):
        data = encode_hr_notification(0)
        assert decode_hr_notification(data) == 0
        data = encode_hr_notification(255)
        assert decode_hr_notification(data) == 255