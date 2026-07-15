"""Verify the ring hardware SDK/API layer imports and works"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'software'))

from ring_ import HardwareRingDataSource, push_hardware_data, SensorData, set_ring_data_source, get_ring_data

# Test SensorData.from_dict
sd = SensorData.from_dict({"bpm": 85, "stress": 40, "mood": "anxious"})
assert sd.bpm == 85, f"Expected bpm=85 got {sd.bpm}"
assert sd.stress == 40, f"Expected stress=40 got {sd.stress}"
assert sd.mood == "anxious", f"Expected mood=anxious got {sd.mood}"
print("OK - SensorData.from_dict")

# Test push_hardware_data
push_hardware_data("test_device", {"bpm": 90, "stress": 50, "spo2": 96})
print("OK - push_hardware_data")

# Test HardwareRingDataSource reads from buffer
source = HardwareRingDataSource()
source.connect("test_device")
data = source.read_sensors()
assert data.bpm == 90, f"Expected bpm=90 got {data.bpm}"
assert data.stress == 50, f"Expected stress=50 got {data.stress}"
assert data.spo2 == 96, f"Expected spo2=96 got {data.spo2}"
print("OK - HardwareRingDataSource reads pushed data")

# Test fallback for unknown device
source2 = HardwareRingDataSource()
source2.connect("unknown")
data2 = source2.read_sensors()
assert data2.bpm > 0, "Expected fallback sensor data"
print("OK - HardwareRingDataSource fallback works")

# Test set_ring_data_source swaps the global source
old_source = get_ring_data("test_device")["bpm"]
set_ring_data_source(source)
new_bpm = get_ring_data("test_device")["bpm"]
assert new_bpm == 90, f"After swap expected bpm=90 got {new_bpm}"
print("OK - set_ring_data_source swap works (bpm=90)")

print("\nAll ring API layer tests passed!")
