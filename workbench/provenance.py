"""Per-report provenance signing.

Every report this tool produces is signed with an Ed25519 key. The signature
covers a content hash plus metadata (candidate id, timestamp, tool version), and
each provenance record carries the signer's public key, so any record is
self-verifying for integrity and attributable to a signer.

Why: if a report is ever altered, or one shows up that this tool did not produce,
the signature makes it detectable and traceable. In a hiring system that informs
decisions about people, "who produced this output, and has it been changed" must
be answerable.

The private key lives in .keys/ (gitignored) and is generated on first use. The
public key travels inside every provenance record, so verification needs no key
distribution. For a real deployment this would use the organization's managed
keys and a post-quantum scheme; Ed25519 keeps the demo standard and inspectable.
"""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

from . import __version__

KEY_DIR = Path(__file__).resolve().parent.parent / ".keys"
KEY_PATH = KEY_DIR / "ed25519.pem"


def _load_or_create_key() -> Ed25519PrivateKey:
    if KEY_PATH.exists():
        return serialization.load_pem_private_key(KEY_PATH.read_bytes(), password=None)
    KEY_DIR.mkdir(exist_ok=True)
    key = Ed25519PrivateKey.generate()
    KEY_PATH.write_bytes(
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    KEY_PATH.chmod(0o600)
    return key


def _pub_hex(pub: Ed25519PublicKey) -> str:
    return pub.public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw
    ).hex()


def sign_report(candidate_id: str, content: str, timestamp: str | None = None) -> dict:
    key = _load_or_create_key()
    content_sha256 = hashlib.sha256(content.encode()).hexdigest()
    record = {
        "candidate_id": candidate_id,
        "content_sha256": content_sha256,
        "tool_version": __version__,
        "signed_at": timestamp or time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "algo": "ed25519",
    }
    message = json.dumps(record, sort_keys=True).encode()
    record["public_key"] = _pub_hex(key.public_key())
    record["signature"] = key.sign(message).hex()
    return record


def verify_record(record: dict, content: str) -> bool:
    """Recompute the hash, rebuild the signed message, check the signature."""
    if hashlib.sha256(content.encode()).hexdigest() != record.get("content_sha256"):
        return False
    signed = {k: record[k] for k in ("candidate_id", "content_sha256", "tool_version", "signed_at", "algo")}
    message = json.dumps(signed, sort_keys=True).encode()
    try:
        pub = Ed25519PublicKey.from_public_bytes(bytes.fromhex(record["public_key"]))
        pub.verify(bytes.fromhex(record["signature"]), message)
        return True
    except Exception:
        return False
