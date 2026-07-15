"""Security benchmark — PBKDF2 latency, crypto overhead, JWT auth handshake."""
import time, os, sys, json, base64
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.kdf.hkdf import HKDFExpand
from jose import jwt

JWT_SECRET = "benchmark-test-secret-key-not-for-production"
JWT_ALGO = "HS256"


def benchmark_pbkdf2(iterations: int, passphrase: str = "benchmark-passphrase-test") -> dict:
    salt = os.urandom(16)
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=iterations)
    t0 = time.perf_counter()
    key = kdf.derive(passphrase.encode())
    elapsed = (time.perf_counter() - t0) * 1000

    hkdf = HKDFExpand(algorithm=hashes.SHA256(), length=32, info=b"sentinel-fernet-key-v1")
    fernet_key = base64.urlsafe_b64encode(hkdf.derive(key))
    f = Fernet(fernet_key)

    encrypt_t0 = time.perf_counter()
    ct = f.encrypt(b"benchmark payload for encryption speed test")
    encrypt_ms = (time.perf_counter() - encrypt_t0) * 1000

    decrypt_t0 = time.perf_counter()
    f.decrypt(ct)
    decrypt_ms = (time.perf_counter() - decrypt_t0) * 1000

    return {
        "iterations": iterations,
        "derive_ms": elapsed,
        "encrypt_ms": encrypt_ms,
        "decrypt_ms": decrypt_ms,
    }


def benchmark_jwt_handshake(payload_size: int = 256) -> dict:
    import string, random
    payload = {
        "sub": "bench_patient_0001",
        "role": "patient",
        "extra": "".join(random.choices(string.ascii_letters, k=payload_size)),
        "iat": int(time.time()),
        "exp": int(time.time()) + 28800,
    }

    t0 = time.perf_counter()
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGO)
    encode_ms = (time.perf_counter() - t0) * 1000

    t0 = time.perf_counter()
    decoded = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGO])
    decode_ms = (time.perf_counter() - t0) * 1000

    return {
        "encode_ms": encode_ms,
        "decode_ms": decode_ms,
        "total_ms": encode_ms + decode_ms,
        "token_len": len(token),
        "payload_valid": decoded.get("sub") == "bench_patient_0001",
    }


def benchmark_crypto_overhead(sizes: list[int] = None) -> list[dict]:
    if sizes is None:
        sizes = [100, 1000, 10000, 100000]
    results = []
    key = Fernet.generate_key()
    cipher = Fernet(key)

    for n_chars in sizes:
        plaintext = "A" * n_chars

        t0 = time.perf_counter()
        ct = cipher.encrypt(plaintext.encode())
        encrypt_ms = (time.perf_counter() - t0) * 1000

        t0 = time.perf_counter()
        pt = cipher.decrypt(ct).decode()
        decrypt_ms = (time.perf_counter() - t0) * 1000

        results.append({
            "payload_bytes": n_chars,
            "ciphertext_bytes": len(ct),
            "encrypt_ms": encrypt_ms,
            "decrypt_ms": decrypt_ms,
            "total_ms": encrypt_ms + decrypt_ms,
            "overhead_bytes": len(ct) - n_chars,
            "verified": pt == plaintext,
        })
    return results


def run_security_benchmarks(log_func, quick=False):
    # 1. PBKDF2 Derivation Latency Sweep
    iterations_list = [10000, 50000, 100000, 300000, 600000]
    if quick:
        iterations_list = [100000, 600000]

    for iters in iterations_list:
        r = benchmark_pbkdf2(iters)
        notes = f"derive={r['derive_ms']:.1f}ms encrypt={r['encrypt_ms']:.1f}ms decrypt={r['decrypt_ms']:.1f}ms"
        passed = r['derive_ms'] < 5000
        log_func(
            "PBKDF2 Key Derivation", 1, "N/A",
            f"{iters} iterations",
            r['derive_ms'], "N/A", passed, notes,
        )

    # 2. Fernet Encrypt/Decrypt Overhead by Payload Size
    sizes = [100, 1000, 10000] if quick else [100, 1000, 10000, 100000]
    overhead_results = benchmark_crypto_overhead(sizes)
    for r in overhead_results:
        overhead_pct = (r['total_ms'] / max(r['payload_bytes'] / 1000, 0.001))
        notes = f"enc={r['encrypt_ms']:.3f}ms dec={r['decrypt_ms']:.3f}ms overhead={r['overhead_bytes']}B"
        log_func(
            "Fernet Crypto Overhead", 1, "N/A",
            f"{r['payload_bytes']}B to {r['ciphertext_bytes']}B",
            r['total_ms'], f"+{r['overhead_bytes']}B", r['verified'], notes,
        )

    # 3. JWT Auth Handshake (simulates WebSocket token verification)
    jwt_sizes = [64, 256, 1024]
    for size in jwt_sizes:
        r = benchmark_jwt_handshake(payload_size=size)
        notes = f"encode={r['encode_ms']:.3f}ms decode={r['decode_ms']:.3f}ms token={r['token_len']}B"
        log_func(
            "JWT Auth Handshake", 1, "N/A",
            f"{size}B claims payload",
            r['total_ms'], f"{r['token_len']}B token", r['payload_valid'], notes,
        )

    # 4. End-to-end: derive key + encrypt + decrypt (full round-trip simulation)
    full_round = benchmark_pbkdf2(600000, "clinician-master-passphrase")
    notes = (f"derive={full_round['derive_ms']:.1f}ms "
             f"encrypt={full_round['encrypt_ms']:.1f}ms "
             f"decrypt={full_round['decrypt_ms']:.1f}ms")
    log_func(
        "Full Crypto Round-Trip (600K iter)", 1, "N/A",
        "derive+enc+dec",
        full_round['derive_ms'] + full_round['encrypt_ms'] + full_round['decrypt_ms'],
        "N/A", full_round['derive_ms'] < 1000, notes,
    )

    # 5. Plaintext vs Encrypted: microbenchmark comparing identical payloads
    plain_sizes = [100, 1000, 10000]
    for n in plain_sizes:
        plain = "X" * n
        key = Fernet.generate_key()
        cipher = Fernet(key)

        t0 = time.perf_counter()
        ct = cipher.encrypt(plain.encode())
        enc_ms = (time.perf_counter() - t0) * 1000

        t0 = time.perf_counter()
        cipher.decrypt(ct)
        dec_ms = (time.perf_counter() - t0) * 1000

        overhead_ms = enc_ms + dec_ms
        log_func(
            "Encrypted Payload Overhead", 1, "N/A",
            f"{n}B plaintext",
            overhead_ms, f"{len(ct)}B ct",
            True,
            f"enc={enc_ms:.3f}ms dec={dec_ms:.3f}ms total={overhead_ms:.3f}ms",
        )
