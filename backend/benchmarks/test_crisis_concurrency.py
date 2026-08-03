"""Crisis concurrency stress test — compressed-time stage transitions."""

import os
import sys
import threading
import time
from dataclasses import dataclass, field

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Time compression: 1 simulated second = 1/TIME_FACTOR real seconds
# TIME_FACTOR=20 means 30 sim-seconds = 1.5 real seconds, 60 sim-seconds = 3 real seconds
TIME_FACTOR = 20


@dataclass
class CrisisSimulator:
    active: bool = False
    triggered_at: float = 0.0
    acknowledged: bool = False
    resolved: bool = False
    stage2_email_sent: bool = False
    stage3_escalation_sent: bool = False
    halted: bool = False
    threads_active: int = 0
    timing_log: list = field(default_factory=list)

    STAGE2_SIM_DELAY = 30.0  # simulated seconds
    STAGE3_SIM_DELAY = 60.0

    @property
    def _stage2_real(self):
        return self.STAGE2_SIM_DELAY / TIME_FACTOR

    @property
    def _stage3_real(self):
        return self.STAGE3_SIM_DELAY / TIME_FACTOR

    def trigger(self):
        self.active = True
        self.triggered_at = time.monotonic()
        self.timing_log.append(("TRIGGER", self.triggered_at, 0.0))

    def acknowledge(self):
        self.acknowledged = True
        now = time.monotonic()
        elapsed_sim = (now - self.triggered_at) * TIME_FACTOR
        self.timing_log.append(("ACK", now, elapsed_sim))
        self.halt()

    def halt(self):
        self.halted = True
        self.active = False
        now = time.monotonic()
        elapsed_sim = (now - self.triggered_at) * TIME_FACTOR
        self.timing_log.append(("HALT", now, elapsed_sim))

    def resolve(self):
        self.resolved = True
        self.active = False

    def run_countdown(self):
        if not self.active:
            return
        self.threads_active += 1
        start = self.triggered_at
        while self.active and not self.halted:
            elapsed_sim = (time.monotonic() - start) * TIME_FACTOR
            if elapsed_sim >= self.STAGE2_SIM_DELAY and not self.stage2_email_sent and not self.halted:
                self.stage2_email_sent = True
                now = time.monotonic()
                self.timing_log.append(("STAGE2_EMAIL", now, (now - start) * TIME_FACTOR))
            if elapsed_sim >= self.STAGE3_SIM_DELAY and not self.stage3_escalation_sent and not self.halted:
                self.stage3_escalation_sent = True
                now = time.monotonic()
                self.timing_log.append(("STAGE3_ESCALATION", now, (now - start) * TIME_FACTOR))
            time.sleep(0.005)
        self.threads_active -= 1


def run_crisis_concurrency_tests(log_func, quick=False):
    loads = [1, 5] if quick else [1, 5, 10, 25]

    for n in loads:
        t0 = time.perf_counter()
        sims = [CrisisSimulator() for _ in range(n)]
        threads = []

        for sim in sims:
            sim.trigger()
            t = threading.Thread(target=sim.run_countdown, daemon=True)
            threads.append(t)
            t.start()

        time.sleep(0.1)
        elapsed = (time.perf_counter() - t0) * 1000

        for sim in sims:
            if not sim.halted:
                sim.acknowledge()

        time.sleep(0.1)
        for sim in sims:
            sim.resolve()
        for t in threads:
            t.join(timeout=0.5)

        dropped = sum(1 for s in sims if s.threads_active > 0)
        stage2_hits = sum(1 for s in sims if s.stage2_email_sent)

        log_func(
            "Crisis Engine",
            n,
            "N/A",
            f"{n} concurrent",
            elapsed,
            f"{dropped} dropped threads",
            dropped == 0,
            f"Stage2 fired={stage2_hits}/{n} (none expected before ack)",
        )

    # Halt Protocol Interruption (compressed time)
    print("  Halt Protocol Interruption...")
    test_cases = [
        ("early (15 sim-s)", 15.0 / TIME_FACTOR, False, False),  # ack before stage 2
        ("mid (45 sim-s)", 45.0 / TIME_FACTOR, True, False),  # ack after stage 2, before stage 3
        ("late (65 sim-s)", 65.0 / TIME_FACTOR, True, True),  # ack after both
    ]
    for _label, real_delay, expect_s2, expect_s3 in test_cases:
        sim = CrisisSimulator()
        sim.trigger()
        t = threading.Thread(target=sim.run_countdown, daemon=True)
        t.start()

        time.sleep(max(real_delay, 0.05))
        if not sim.halted:
            sim.acknowledge()

        time.sleep(0.1)
        sim.resolve()
        t.join(timeout=0.5)

        halted = sim.halted
        stage2 = sim.stage2_email_sent
        stage3 = sim.stage3_escalation_sent
        halt_elapsed = next((e[2] for e in sim.timing_log if e[0] == "HALT"), 0)

        ok = halted and (stage2 == expect_s2) and (stage3 == expect_s3)

        log_func(
            "Halt Protocol",
            1,
            "N/A (compressed)",
            f"ack @ {real_delay * TIME_FACTOR:.0f} sim-s",
            halt_elapsed * 1000 / TIME_FACTOR if halt_elapsed else 0,
            f"s2={'y' if stage2 else 'n'} s3={'y' if stage3 else 'n'}",
            ok,
            f"halt_sim_elapsed={halt_elapsed:.1f}s",
        )
