import logging
import threading
import time
from collections import deque
from collections.abc import Callable
from typing import Any

logger = logging.getLogger("sentinel.ai_queue")


class AILimiter:
    def __init__(self, max_concurrent: int = 2, min_interval: float = 1.0):
        self.max_concurrent = max_concurrent
        self.min_interval = min_interval
        self._lock = threading.Lock()
        self._running = 0
        self._last_call = 0.0
        self._queue: deque = deque()
        self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._worker_thread.start()

    def submit(self, fn: Callable, *args, **kwargs) -> Any:
        result = {"value": None, "error": None, "done": threading.Event()}

        def _wrapper():
            try:
                with self._lock:
                    self._running += 1
                now = time.time()
                wait = self.min_interval - (now - self._last_call)
                if wait > 0:
                    time.sleep(wait)
                self._last_call = time.time()
                result["value"] = fn(*args, **kwargs)
            except Exception as e:
                result["error"] = e
                logger.exception("AI queue job failed: %s", e)
            finally:
                with self._lock:
                    self._running -= 1
                result["done"].set()

        self._queue.append(_wrapper)
        result["done"].wait(timeout=120)
        if result["error"]:
            raise result["error"]
        return result["value"]

    def _worker_loop(self):
        while True:
            if self._queue:
                with self._lock:
                    if self._running < self.max_concurrent and self._queue:
                        job = self._queue.popleft()
                        threading.Thread(target=job, daemon=True).start()
            time.sleep(0.1)

    @property
    def pending(self) -> int:
        return len(self._queue)

    @property
    def running(self) -> int:
        with self._lock:
            return self._running


ai_limiter = AILimiter(max_concurrent=2, min_interval=1.0)
