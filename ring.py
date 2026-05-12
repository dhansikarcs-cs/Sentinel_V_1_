import random
from datetime import datetime


def get_ring_data(username: str, intensity: float = 1.0):
    seed = hash(username + datetime.now().strftime("%Y%m%d%H")) % (2**31)
    rng = random.Random(seed)

    base_bpm = 72 + rng.randint(-8, 8)
    bpm = int(base_bpm * (0.9 + 0.2 * intensity))

    stress = min(100, max(5, int(rng.gauss(35, 15) * intensity)))
    sleep_hours = round(max(3, min(10, rng.gauss(7, 1.2) - (intensity - 1) * 0.5)), 1)
    spo2 = round(min(100, max(90, rng.gauss(97, 1.0) - (intensity - 1) * 0.3)), 1)

    mood_options = ["calm", "neutral", "anxious", "sad", "happy", "irritable", "fatigued"]
    weights = [0.2, 0.3, 0.15, 0.1, 0.1, 0.05, 0.1]
    if intensity > 1.3:
        weights = [0.05, 0.15, 0.25, 0.2, 0.02, 0.2, 0.13]
    mood = rng.choices(mood_options, weights=weights, k=1)[0]

    return {
        "bpm": bpm,
        "stress": stress,
        "sleep": sleep_hours,
        "mood": mood,
        "spo2": spo2,
    }


def get_seeded_history(username: str, metric: str, hours: int = 24):
    base_seed = hash(username) % (2**31)
    values = []
    rng = random.Random(base_seed)
    base_val = {
        "bpm": 72, "stress": 35, "sleep": 7, "spo2": 97, "mood_score": 5
    }.get(metric, 50)

    for i in range(hours):
        rng = random.Random(base_seed + i * 1000)
        variation = rng.gauss(0, base_val * 0.12)
        val = max(0, min(100, base_val + variation))
        if metric == "sleep":
            val = max(0, min(10, base_val + rng.gauss(0, 1.5)))
        values.append(round(val, 1))

    return values
