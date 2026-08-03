"""50 test profiles for discrepancy detection + 50 journal entries for AI benchmark."""

import csv
from dataclasses import dataclass

# ── Discrepancy Test Profiles ──


@dataclass
class DiscrepancyProfile:
    id: int
    journal_text: str
    bpm: int
    hrv: int
    expected_discrepancy: bool
    category: str  # "text-biometric mismatch" | "text-biometric match"


DISCREPANCY_PROFILES: list[DiscrepancyProfile] = [
    # === MISMATCHES (text says good, biometrics say bad) ===
    DiscrepancyProfile(1, "I feel great today", 130, 15, True, "text-biometric mismatch"),
    DiscrepancyProfile(2, "Best day ever! So happy and energetic.", 125, 18, True, "text-biometric mismatch"),
    DiscrepancyProfile(3, "Everything is perfect, life is wonderful", 140, 12, True, "text-biometric mismatch"),
    DiscrepancyProfile(4, "I'm doing amazing, never been better", 118, 20, True, "text-biometric mismatch"),
    DiscrepancyProfile(5, "Feeling fantastic and full of energy", 135, 14, True, "text-biometric mismatch"),
    DiscrepancyProfile(6, "What a great morning! So refreshed.", 128, 16, True, "text-biometric mismatch"),
    DiscrepancyProfile(7, "I'm so happy I could dance all day", 142, 11, True, "text-biometric mismatch"),
    DiscrepancyProfile(8, "Life is good, really good", 120, 19, True, "text-biometric mismatch"),
    DiscrepancyProfile(9, "Feeling on top of the world", 145, 10, True, "text-biometric mismatch"),
    DiscrepancyProfile(10, "I'm cured. Therapy worked perfectly.", 122, 17, True, "text-biometric mismatch"),
    # === MISMATCHES (text says bad, biometrics say calm) ===
    DiscrepancyProfile(11, "I'm extremely anxious and can't cope", 65, 70, True, "text-biometric mismatch"),
    DiscrepancyProfile(12, "I want to disappear, I'm so scared", 68, 72, True, "text-biometric mismatch"),
    DiscrepancyProfile(13, "My anxiety is through the roof today", 62, 75, False, "text-biometric mismatch"),
    DiscrepancyProfile(14, "I'm having a panic attack right now", 70, 68, True, "text-biometric mismatch"),
    DiscrepancyProfile(15, "I can't breathe, I'm so terrified", 66, 74, True, "text-biometric mismatch"),
    DiscrepancyProfile(16, "The fear is overwhelming me", 63, 76, True, "text-biometric mismatch"),
    DiscrepancyProfile(17, "I'm losing my mind with worry", 69, 71, False, "text-biometric mismatch"),
    DiscrepancyProfile(18, "I think I'm going crazy", 64, 73, False, "text-biometric mismatch"),
    DiscrepancyProfile(19, "My heart is racing from fear", 67, 69, True, "text-biometric mismatch"),
    DiscrepancyProfile(20, "I'm terrified of what's happening to me", 61, 77, True, "text-biometric mismatch"),
    # === MATCHES (positive text + calm biometrics) ===
    DiscrepancyProfile(21, "I feel great today", 72, 65, False, "text-biometric match"),
    DiscrepancyProfile(22, "Happy and relaxed", 70, 68, False, "text-biometric match"),
    DiscrepancyProfile(23, "Feeling peaceful and content", 68, 72, False, "text-biometric match"),
    DiscrepancyProfile(24, "What a calm, lovely day", 71, 70, False, "text-biometric match"),
    DiscrepancyProfile(25, "I'm doing well today", 69, 74, False, "text-biometric match"),
    DiscrepancyProfile(26, "Enjoying a quiet afternoon", 73, 66, False, "text-biometric match"),
    DiscrepancyProfile(27, "Things are looking up", 70, 69, False, "text-biometric match"),
    DiscrepancyProfile(28, "Had a good therapy session", 72, 71, False, "text-biometric match"),
    DiscrepancyProfile(29, "Feeling grateful today", 68, 73, False, "text-biometric match"),
    DiscrepancyProfile(30, "I'm optimistic about the future", 71, 67, False, "text-biometric match"),
    # === MATCHES (negative text + high stress biometrics) ===
    DiscrepancyProfile(31, "I'm extremely anxious and can't cope", 128, 18, False, "text-biometric match"),
    DiscrepancyProfile(32, "I feel terrible today", 132, 14, False, "text-biometric match"),
    DiscrepancyProfile(33, "Everything is falling apart", 140, 11, False, "text-biometric match"),
    DiscrepancyProfile(34, "I can't handle this anymore", 135, 13, False, "text-biometric match"),
    DiscrepancyProfile(35, "The stress is killing me", 142, 10, False, "text-biometric match"),
    DiscrepancyProfile(36, "I feel so alone and scared", 130, 16, False, "text-biometric match"),
    DiscrepancyProfile(37, "Nothing makes sense anymore", 138, 12, False, "text-biometric match"),
    DiscrepancyProfile(38, "I'm drowning in anxiety", 145, 9, False, "text-biometric match"),
    DiscrepancyProfile(39, "Today is unbearable", 136, 15, False, "text-biometric match"),
    DiscrepancyProfile(40, "I just want to sleep forever", 129, 17, False, "text-biometric match"),
    # === EDGE CASES ===
    DiscrepancyProfile(41, "", 72, 65, False, "edge-empty text"),
    DiscrepancyProfile(42, "Fine.", 130, 15, True, "edge-minimal text + high stress"),
    DiscrepancyProfile(43, "A" * 2000, 72, 65, False, "edge-very long repetitive text + calm"),
    DiscrepancyProfile(44, "Fine.", 72, 65, False, "edge-minimal text + calm"),
    DiscrepancyProfile(45, "I feel great today", 0, 0, False, "edge-zero biometrics"),
    DiscrepancyProfile(46, "I want to die", 72, 65, True, "edge-crisis text + calm biometrics"),
    DiscrepancyProfile(47, "I'm going to kill myself tonight", 68, 70, True, "edge-suicidal text + calm biometrics"),
    DiscrepancyProfile(48, "I want to die", 140, 10, False, "edge-crisis text + high stress"),
    DiscrepancyProfile(49, "Neutral nothing special", 100, 40, False, "edge-neutral text + moderate stress"),
    DiscrepancyProfile(50, "I'm feeling quite neutral today", 130, 15, True, "edge-neutral text + high stress"),
]


# ── AI Benchmark Journal Entries ──


@dataclass
class JournalBenchEntry:
    id: int
    text: str
    word_count: int


def _generate_entries() -> list[JournalBenchEntry]:
    entries = []
    base_texts = [
        "Today was a challenging day. I woke up feeling anxious about the meeting at work. "
        "My heart was racing as I thought about presenting to the team. I took some deep breaths "
        "and tried to focus on the present moment. The meeting went better than expected, "
        "but I still felt on edge afterwards. I'm learning to manage these feelings.",
        "I had a wonderful day today. The sun was shining and I went for a long walk in the park. "
        "I saw children playing and couples laughing. It made me feel hopeful about life. "
        "I called my sister and we talked for an hour. She always knows how to make me feel better. "
        "I'm grateful for these small moments of peace.",
        "I'm struggling. The darkness feels like it's closing in and I can't find a way out. "
        "I tried to reach out to a friend but they didn't answer. I feel so alone in this. "
        "The medication doesn't seem to be working anymore. I don't know how much longer "
        "I can keep fighting this battle. Every day feels like an uphill climb.",
        "Therapy session was intense today. We talked about my childhood and I had a breakthrough "
        "about why I struggle with trust. It was painful but cathartic. Dr. X said I'm making "
        "real progress. I've been consistent with my journaling and mindfulness exercises. "
        "Small steps forward every day.",
        "I feel numb. Not sad, not happy, just... nothing. I went through the motions today. "
        "Ate breakfast, went to work, came home, watched TV, went to bed. Is this what life is? "
        "I keep waiting for something to change but nothing does. Maybe this is just how it is.",
    ]

    for _, bt in enumerate(base_texts):
        for multiplier, _ in [(1, "100w"), (2, "250w"), (5, "500w"), (10, "1000w")]:
            text = " ".join([bt] * multiplier)
            wc = len(text.split())
            entries.append(
                JournalBenchEntry(
                    id=len(entries) + 1,
                    text=text,
                    word_count=wc,
                )
            )
    # Fill remaining up to 50 with variations
    while len(entries) < 50:
        i = len(entries) % len(base_texts)
        bt = base_texts[i]
        import random

        noise = " " + " ".join(["word"] * random.randint(10, 50))
        entries.append(
            JournalBenchEntry(
                id=len(entries) + 1,
                text=bt + noise,
                word_count=len((bt + noise).split()),
            )
        )

    return entries[:50]


AI_BENCH_ENTRIES = _generate_entries()


# ── CSV Writer ──

LOGBOOK_HEADERS = [
    "Run ID",
    "Component Tested",
    "Concurrency Load",
    "AI Mode",
    "Input Size (Words/Bytes)",
    "Latency (ms)",
    "CPU/RAM Peak",
    "Pass/Fail",
    "Notes / Error Caught",
]


def init_logbook(path: str):
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(LOGBOOK_HEADERS)


def append_logbook(path: str, row: dict):
    with open(path, "a", newline="") as f:
        w = csv.writer(f)
        w.writerow([row.get(h, "") for h in LOGBOOK_HEADERS])
