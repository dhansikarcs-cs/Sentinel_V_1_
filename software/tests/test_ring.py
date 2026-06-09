import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ring_ import (
    SensorData, IMUData, SimulatedRing, RingDataSource,
    encode_hr_notification, decode_hr_notification,
    encode_imu_data, decode_imu_data,
    encode_ppg_sample,
    get_ring_data, get_seeded_history,
)


class TestRingModels:
    def test_sensor_data_defaults(self):
        d = SensorData()
        assert d.bpm == 72
        assert d.stress == 35
        assert d.sleep == 7.0
        assert d.spo2 == 97.0
        assert d.mood == "neutral"
        assert d.temperature == 36.5

    def test_imu_defaults(self):
        imu = IMUData()
        assert imu.accel_x == 0.0
        assert imu.accel_y == 0.0
        assert imu.accel_z == 0.0

    def test_sensor_data_to_dict(self):
        d = SensorData(bpm=80, stress=50, mood="anxious")
        d_dict = d.to_dict()
        assert d_dict["bpm"] == 80
        assert d_dict["stress"] == 50
        assert d_dict["mood"] == "anxious"
        assert "imu" in d_dict
        assert d_dict["imu"]["accel_x"] == 0.0

    def test_imu_in_sensor_data(self):
        imu = IMUData(accel_x=1.0, accel_y=2.0, accel_z=9.81)
        d = SensorData(imu=imu)
        assert d.imu.accel_x == 1.0
        assert d.imu.accel_z == 9.81


class TestRingProtocol:
    def test_encode_hr_uint8(self):
        data = encode_hr_notification(72)
        assert len(data) == 2
        assert data[0] == 0  # flags = 0 (uint8)
        assert data[1] == 72

    def test_decode_hr_uint8(self):
        data = encode_hr_notification(85)
        bpm = decode_hr_notification(data)
        assert bpm == 85

    def test_encode_ppg(self):
        data = encode_ppg_sample(1024, 0)
        assert len(data) == 4

    def test_encode_imu(self):
        accel = (1000, -500, 9800)
        gyro = (2500, -1000, 500)
        data = encode_imu_data(accel, gyro)
        assert len(data) == 12
        decoded = decode_imu_data(data)
        assert decoded["accel_mg"] == (1000, -500, 9800)
        assert decoded["gyro_mdps"] == (2500, -1000, 500)

    def test_imu_roundtrip(self):
        accel = (0, 0, 9810)
        gyro = (0, 0, 0)
        data = encode_imu_data(accel, gyro)
        decoded = decode_imu_data(data)
        assert decoded["accel_mg"] == (0, 0, 9810)


class TestSimulatedRing:
    def test_connect(self):
        ring = SimulatedRing()
        assert ring.connect("test-device") is True
        assert ring.device_id == "test-device"

    def test_read_sensors_returns_valid(self):
        ring = SimulatedRing()
        ring.device_id = "test"
        data = ring.read_sensors()
        assert isinstance(data, SensorData)
        assert 40 <= data.bpm <= 120
        assert 0 <= data.stress <= 100
        assert 3 <= data.sleep <= 10
        assert 90 <= data.spo2 <= 100

    def test_intensity_affects_stress(self):
        ring = SimulatedRing()
        ring.device_id = "test"
        low = ring.read_sensors(0.5)
        high = ring.read_sensors(2.0)
        assert high.stress >= low.stress

    def test_get_seeded_history(self):
        ring = SimulatedRing()
        ring.device_id = "test"
        vals = ring.get_seeded_history("bpm", 24)
        assert len(vals) == 24
        assert all(isinstance(v, (int, float)) for v in vals)

    def test_seeded_history_consistent(self):
        ring = SimulatedRing()
        ring.device_id = "test"
        v1 = ring.get_seeded_history("stress", 5)
        v2 = ring.get_seeded_history("stress", 5)
        assert v1 == v2

    def test_ring_data_source_interface(self):
        assert issubclass(SimulatedRing, RingDataSource)

    def test_disconnect(self):
        ring = SimulatedRing()
        ring.connect("test")
        ring.disconnect()
        assert ring.streaming is False

    def test_streaming(self):
        ring = SimulatedRing()
        ring.connect("test")
        results = []
        def collect(d):
            results.append(d)
            ring.stop_streaming()
        import threading
        t = threading.Thread(target=ring.start_streaming, args=(collect,), daemon=True)
        t.start()
        t.join(timeout=2)
        assert len(results) == 1
        assert isinstance(results[0], SensorData)


class TestBackwardCompat:
    def test_get_ring_data(self):
        data = get_ring_data("test_patient_1")
        assert "bpm" in data
        assert "stress" in data
        assert "sleep" in data
        assert "spo2" in data
        assert "mood" in data

    def test_get_seeded_history(self):
        vals = get_seeded_history("test_patient_1", "bpm", 10)
        assert len(vals) == 10
        assert all(isinstance(v, (int, float)) for v in vals)


if __name__ == "__main__":
    import pytest
    pytest.main([__file__])