"""Encrypted, off-box backup for the Sentinel SQLite database (Issue 15).

Addresses the "backups live in the same ephemeral container" gap:

1. Makes a consistent snapshot with the SQLite online-backup API (safe under WAL).
2. Encrypts it with Fernet using BACKUP_KEY (or a derived key when not set).
3. Writes to a durable local target and, when S3-compatible env vars are present,
   uploads the ciphertext to object storage (AWS S3 / Cloudflare R2 / MinIO / etc.).
4. Keeps the last N local backups.

Usage:
    python -m scripts.backup_db [--out <dir>] [--keep <n>]
    SENTINEL_BACKUP_KEY=<fernet-key> python -m scripts.backup_db
    # or S3 off-box:
    SENTINEL_BACKUP_KEY=... \
    S3_ENDPOINT_URL=https://... S3_BUCKET=sentinel-backups \
    S3_ACCESS_KEY=... S3_SECRET_KEY=... \
    python -m scripts.backup_db

The backup file is encrypted before leaving the machine; object storage never sees
plaintext PHI. The Fernet key must be kept separately from the data it protects.
"""

import argparse
import base64
import getpass
import glob
import hashlib
import hmac
import logging
import os
import sqlite3
import sys
from datetime import UTC, datetime
from pathlib import Path

import requests
from cryptography.fernet import Fernet

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("sentinel.backup")

BACKUP_KEY_ENV = "SENTINEL_BACKUP_KEY"
S3_ENDPOINT_ENV = "S3_ENDPOINT_URL"
S3_BUCKET_ENV = "S3_BUCKET"
S3_ACCESS_KEY_ENV = "S3_ACCESS_KEY"
S3_SECRET_KEY_ENV = "S3_SECRET_KEY"
S3_REGION_ENV = "S3_REGION"

DEFAULT_DB = "sqlite:///./data/sentinel.db"
SERVICE_NAME = "s3"
AWS4_ALGORITHM = "AWS4-HMAC-SHA256"
UNSIGNED_PAYLOAD = "UNSIGNED-PAYLOAD"


def resolve_db_path(db_arg: str | None) -> str:
    db = db_arg or os.environ.get("DATABASE_URL", DEFAULT_DB)
    if db.startswith("sqlite:///"):
        return db[len("sqlite:///") :]
    return db


def consistent_snapshot(db_path: str, dest: Path) -> None:
    """Use the SQLite online backup API so the copy is consistent even mid-write."""
    src = sqlite3.connect(db_path)
    try:
        dst = sqlite3.connect(str(dest))
        try:
            src.backup(dst)
        finally:
            dst.close()
    finally:
        src.close()


def _key_bytes() -> bytes:
    key = os.environ.get(BACKUP_KEY_ENV, "")
    if key:
        return key.encode("utf-8")
    digest = hashlib.sha256((getpass.getuser() + "|" + SERVICE_NAME).encode("utf-8")).digest()
    logger.warning(
        "SENTINEL_BACKUP_KEY not set — deriving a machine-local key. "
        "Set it explicitly for recoverable backups on another host."
    )
    return base64.urlsafe_b64encode(digest)


def aws4_signed_headers(headers: dict[str, str]) -> str:
    return ";".join(k.lower() for k in sorted(headers))


def aws4_hmac(key: bytes, msg: str) -> bytes:
    return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()


def aws4_signing_key(secret: str, date_stamp: str, region: str, service: str = SERVICE_NAME) -> bytes:
    k_date = aws4_hmac(("AWS4" + secret).encode("utf-8"), date_stamp)
    k_region = aws4_hmac(k_date, region)
    k_service = aws4_hmac(k_region, service)
    return aws4_hmac(k_service, "aws4_request")


def upload_to_s3(path: Path, object_key: str) -> None:
    endpoint = os.environ.get(S3_ENDPOINT_ENV, "").rstrip("/")
    bucket = os.environ.get(S3_BUCKET_ENV, "")
    access_key = os.environ.get(S3_ACCESS_KEY_ENV, "")
    secret_key = os.environ.get(S3_SECRET_KEY_ENV, "")
    region = os.environ.get(S3_REGION_ENV, "us-east-1")
    if not (endpoint and bucket and access_key and secret_key):
        logger.info("S3 env vars not fully set — skipping off-box upload (local encrypted copy only).")
        return

    now = datetime.now(UTC)
    amz_date = now.strftime("%Y%m%dT%H%M%SZ")
    date_stamp = now.strftime("%Y%m%d")

    payload = path.read_bytes()
    canonical_uri = f"/{bucket}/{object_key}"
    host = endpoint.replace("https://", "").replace("http://", "")
    headers = {
        "host": host,
        "x-amz-content-sha256": UNSIGNED_PAYLOAD,
        "x-amz-date": amz_date,
    }
    signed_headers = aws4_signed_headers(headers)
    canonical_query = ""
    canonical_request = "\n".join(
        [
            "PUT",
            canonical_uri,
            canonical_query,
            "".join(f"{k.lower()}:{v}\n" for k, v in sorted(headers.items())),
            signed_headers,
            UNSIGNED_PAYLOAD,
        ]
    )
    credential_scope = f"{date_stamp}/{region}/{SERVICE_NAME}/aws4_request"
    string_to_sign = "\n".join(
        [
            AWS4_ALGORITHM,
            amz_date,
            credential_scope,
            hashlib.sha256(canonical_request.encode("utf-8")).hexdigest(),
        ]
    )
    signing_key = aws4_signing_key(secret_key, date_stamp, region)
    signature = hmac.new(signing_key, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()
    authorization = (
        f"{AWS4_ALGORITHM} Credential={access_key}/{credential_scope}, "
        f"SignedHeaders={signed_headers}, Signature={signature}"
    )

    req_headers = {
        "x-amz-date": amz_date,
        "x-amz-content-sha256": UNSIGNED_PAYLOAD,
        "Authorization": authorization,
    }
    url = f"{endpoint}/{bucket}/{object_key}"
    resp = requests.put(url, data=payload, headers=req_headers, timeout=300)
    if resp.status_code not in (200, 201):
        raise RuntimeError(f"S3 upload failed: HTTP {resp.status_code} {resp.text[:300]}")
    logger.info("Uploaded encrypted backup to %s (bucket=%s, %d bytes)", object_key, bucket, len(payload))


def prune_local(out_dir: Path, keep: int, pattern: str) -> None:
    files = sorted(glob.glob(str(out_dir / pattern)))
    while len(files) > keep:
        Path(files.pop(0)).unlink(missing_ok=True)
        logger.info("Pruned old backup %s", files)


def main() -> None:
    parser = argparse.ArgumentParser(description="Sentinel encrypted off-box DB backup")
    parser.add_argument("--db", help=f"SQLite path or DATABASE_URL (default: {DEFAULT_DB})")
    parser.add_argument("--out", default="./data/backups", help="durable local backup directory")
    parser.add_argument("--keep", type=int, default=7, help="number of local backups to retain")
    parser.add_argument("--no-s3", action="store_true", help="skip S3 upload even if configured")
    args = parser.parse_args()

    db_path = resolve_db_path(args.db)
    if not os.path.exists(db_path):
        logger.error("Database not found at %s", db_path)
        sys.exit(1)

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    stamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    plain = out_dir / f"sentinel_{stamp}.db"
    enc = out_dir / f"sentinel_{stamp}.db.enc"

    consistent_snapshot(db_path, plain)
    logger.info("Consistent snapshot written to %s (%d bytes)", plain, plain.stat().st_size)

    key = _key_bytes()
    cipher = Fernet(key)
    enc.write_bytes(cipher.encrypt(plain.read_bytes()))
    plain.unlink()
    logger.info("Encrypted to %s (%d bytes)", enc, enc.stat().st_size)

    if not args.no_s3:
        upload_to_s3(enc, enc.name)

    prune_local(out_dir, args.keep, "sentinel_*.db.enc")
    logger.info("Backup complete. Keep SENTINEL_BACKUP_KEY separate from the backup files.")


if __name__ == "__main__":
    main()
