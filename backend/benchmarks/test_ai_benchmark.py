"""AI provider benchmark — Mock/Ollama/Groq TTFT + total latency."""

import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from benchmarks.profiles import AI_BENCH_ENTRIES


def _try_provider(text: str, provider: str, url: str = "", model: str = "") -> dict:
    """Attempt to call an AI provider. Returns timing data or fallback."""
    t0 = time.perf_counter()
    result = {"success": False, "ttft_ms": 0, "total_ms": 0, "output_len": 0, "error": ""}

    if provider == "mock":
        # Simulate AI processing for environments without Ollama/Groq
        time.sleep(0.05)  # simulate 50ms compute
        ttft = (time.perf_counter() - t0) * 1000
        summary = f"Simulated summary of {len(text.split())} words."
        total = (time.perf_counter() - t0) * 1000
        return {
            "success": True,
            "ttft_ms": ttft,
            "total_ms": total,
            "output_len": len(summary.split()),
            "output": summary,
            "provider": provider,
        }

    if provider == "ollama":
        try:
            import urllib.request

            data = json.dumps(
                {"model": model or "mistral", "prompt": f"Summarize: {text[:500]}", "stream": False}
            ).encode()
            req = urllib.request.Request(
                url or "http://localhost:11434/api/generate", data=data, headers={"Content-Type": "application/json"}
            )
            t_first = time.perf_counter()
            resp = urllib.request.urlopen(req, timeout=30)
            ttft = (time.perf_counter() - t_first) * 1000
            result["ttft_ms"] = ttft
            body = json.loads(resp.read().decode())
            total = (time.perf_counter() - t0) * 1000
            result["total_ms"] = total
            result["output"] = body.get("response", "")
            result["output_len"] = len(result["output"].split())
            result["success"] = True
        except Exception as e:
            result["error"] = str(e)
        return result

    if provider == "groq":
        try:
            import urllib.request

            api_key = os.environ.get("GROQ_API_KEY", "")
            if not api_key:
                return {**result, "error": "GROQ_API_KEY not set"}
            data = json.dumps(
                {
                    "model": model or "mixtral-8x7b-32768",
                    "messages": [
                        {"role": "user", "content": f"Summarize this journal entry in 1-2 sentences:\n\n{text}"}
                    ],
                }
            ).encode()
            req = urllib.request.Request(
                "https://api.groq.com/openai/v1/chat/completions",
                data=data,
                headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
            )
            t_first = time.perf_counter()
            resp = urllib.request.urlopen(req, timeout=60)
            ttft = (time.perf_counter() - t_first) * 1000
            result["ttft_ms"] = ttft
            body = json.loads(resp.read().decode())
            total = (time.perf_counter() - t0) * 1000
            result["total_ms"] = total
            result["output"] = body.get("choices", [{}])[0].get("message", {}).get("content", "")
            result["output_len"] = len(result["output"].split())
            result["success"] = True
        except Exception as e:
            result["error"] = str(e)
        return result

    return {**result, "error": f"Unknown provider: {provider}"}


def run_ai_benchmarks(log_func, quick=False):
    entries = AI_BENCH_ENTRIES[:10] if quick else AI_BENCH_ENTRIES

    # Group by word count
    from collections import defaultdict

    by_wc = defaultdict(list)
    for e in entries:
        bucket = (
            "100w"
            if e.word_count <= 150
            else "250w"
            if e.word_count <= 350
            else "500w"
            if e.word_count <= 750
            else "1000w"
        )
        by_wc[bucket].append(e)

    # Mock provider (always available)
    print("  Mock AI (baseline)...")
    for bucket, items in by_wc.items():
        latencies = []
        for entry in items[:2]:
            r = _try_provider(entry.text, "mock")
            if r["success"]:
                latencies.append(r["total_ms"])
        avg_lat = sum(latencies) / len(latencies) if latencies else 0

        log_func(
            "AI Summarizer",
            1,
            "Mock",
            f"{bucket} ({len(items)} entries)",
            avg_lat,
            "N/A",
            True,
            f"avg {avg_lat:.1f}ms/{bucket}",
        )

    # Ollama (if available)
    print("  Ollama (local)...")
    ollama_ok = False
    try:
        import urllib.request

        r = urllib.request.urlopen("http://localhost:11434/api/tags", timeout=3)
        ollama_ok = r.status == 200
    except Exception:
        pass

    if ollama_ok:
        for bucket, items in by_wc.items():
            latencies = []
            for entry in items[:1]:
                r = _try_provider(entry.text, "ollama")
                if r["success"]:
                    latencies.append(r["total_ms"])
            avg_lat = sum(latencies) / len(latencies) if latencies else 0
            log_func(
                "AI Summarizer",
                1,
                "Ollama (Mistral)",
                f"{bucket}",
                avg_lat,
                "Local CPU/RAM varies",
                len(latencies) > 0,
                f"TTFT avg -- {avg_lat:.1f}ms total",
            )
    else:
        log_func(
            "AI Summarizer",
            1,
            "Ollama (Mistral)",
            "N/A (not running)",
            0,
            "N/A",
            False,
            "Ollama not available on this host",
        )

    # Groq (if API key set)
    print("  Groq (cloud)...")
    if os.environ.get("GROQ_API_KEY"):
        for bucket, items in by_wc.items():
            latencies = []
            for entry in items[:1]:
                r = _try_provider(entry.text, "groq")
                if r["success"]:
                    latencies.append(r["total_ms"])
            avg_lat = sum(latencies) / len(latencies) if latencies else 0
            log_func(
                "AI Summarizer",
                1,
                "Groq Cloud",
                f"{bucket}",
                avg_lat,
                "Cloud API",
                len(latencies) > 0,
                f"TTFT avg -- {avg_lat:.1f}ms total",
            )
    else:
        log_func(
            "AI Summarizer", 1, "Groq Cloud", "N/A (no key)", 0, "N/A", False, "Set GROQ_API_KEY env var to enable"
        )
