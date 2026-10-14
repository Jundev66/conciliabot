from __future__ import annotations

import base64
import hashlib
import ipaddress
import os
import secrets
import socket
import threading
import time
from typing import Optional
from urllib.parse import urlsplit

from . import config


class UnsafeUrlError(ValueError):
    """Raised when an outbound URL targets a disallowed destination."""


_METADATA_HOSTS = {
    "metadata",
    "metadata.google.internal",
    "instance-data",
    "metadata.aws.internal",
}


def _key_bytes(material: str) -> bytes:
    try:
        raw = base64.b64decode(material)
    except Exception:  # noqa: BLE001
        raw = b""
    if len(raw) not in (16, 24, 32):
        raw = hashlib.sha256((material or "").encode("utf-8")).digest()
    return raw


def _resolve_ips(host: str) -> list[ipaddress._BaseAddress]:
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror as exc:
        raise UnsafeUrlError(f"no se pudo resolver el host '{host}': {exc}") from exc
    ips: list[ipaddress._BaseAddress] = []
    for info in infos:
        addr = info[4][0]
        try:
            ips.append(ipaddress.ip_address(addr))
        except ValueError:
            continue
    if not ips:
        raise UnsafeUrlError(f"el host '{host}' no resolvio a ninguna IP")
    return ips


def _blocked(ip: ipaddress._BaseAddress) -> bool:
    # Always refuse cloud metadata / link-local / multicast / reserved targets.
    if ip.is_link_local or ip.is_multicast or ip.is_reserved or ip.is_unspecified:
        return True
    if not config.ALLOW_PRIVATE_NETWORKS and (ip.is_private or ip.is_loopback):
        return True
    return False


def validate_outbound_url(url: str, purpose: str = "salida") -> str:
    """Validate an outbound URL against the SSRF policy; returns it unchanged.

    Only http/https are allowed. Link-local/metadata/reserved ranges are always
    blocked; private and loopback ranges are blocked too when
    ``CONCILIABOT_ALLOW_PRIVATE`` is off (BYOC defaults to on, since the ERP
    usually lives on the LAN).
    """
    text = (url or "").strip()
    if not text:
        raise UnsafeUrlError(f"URL vacia ({purpose})")
    parts = urlsplit(text)
    if parts.scheme not in ("http", "https"):
        raise UnsafeUrlError(f"esquema no permitido '{parts.scheme}' ({purpose}); usa http/https")
    host = parts.hostname
    if not host:
        raise UnsafeUrlError(f"URL sin host ({purpose})")
    if host.lower() in _METADATA_HOSTS:
        raise UnsafeUrlError(f"host de metadatos bloqueado '{host}' ({purpose})")
    for ip in _resolve_ips(host):
        if _blocked(ip):
            raise UnsafeUrlError(f"destino no permitido {ip} ({purpose})")
    return text


def is_loopback(host: Optional[str]) -> bool:
    if not host:
        return False
    if host in ("localhost",):
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


_ENC_PREFIX = "enc:v1:"


def is_encrypted(value: str) -> bool:
    return isinstance(value, str) and value.startswith(_ENC_PREFIX)


def encrypt_secret(plaintext: str) -> str:
    """Encrypt a secret for storage (AES-256-GCM). Plaintext if no key/library."""
    if not plaintext or not config.DB_ENCRYPTION_KEY:
        return plaintext
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    except Exception:  # noqa: BLE001 - encryption is optional
        return plaintext
    nonce = os.urandom(12)
    ciphertext = AESGCM(_key_bytes(config.DB_ENCRYPTION_KEY)).encrypt(
        nonce, plaintext.encode("utf-8"), None
    )
    blob = base64.urlsafe_b64encode(nonce + ciphertext).decode("ascii")
    return f"{_ENC_PREFIX}{blob}"


def decrypt_secret(value: str) -> str:
    if not is_encrypted(value):
        return value
    key = config.DB_ENCRYPTION_KEY
    if not key:
        return ""
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    except Exception:  # noqa: BLE001
        return ""
    try:
        blob = base64.urlsafe_b64decode(value[len(_ENC_PREFIX) :])
        nonce, ciphertext = blob[:12], blob[12:]
        return AESGCM(_key_bytes(key)).decrypt(nonce, ciphertext, None).decode("utf-8")
    except Exception:  # noqa: BLE001
        return ""


def load_or_create_token() -> str:
    """Local API token. Uses the env override, else a generated data/api_token."""
    if config.AUTH_TOKEN:
        return config.AUTH_TOKEN
    path = config.AUTH_TOKEN_FILE
    try:
        if path.exists():
            token = path.read_text(encoding="utf-8").strip()
            if token:
                return token
        token = secrets.token_urlsafe(32)
        path.write_text(token, encoding="utf-8")
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass
        return token
    except OSError:
        return secrets.token_urlsafe(32)


def token_matches(provided: Optional[str], expected: Optional[str]) -> bool:
    if not provided or not expected:
        return False
    return secrets.compare_digest(provided, expected)


def bearer_token(authorization: Optional[str], header_token: Optional[str]) -> str:
    if provided := (header_token or "").strip():
        return provided
    header = (authorization or "").strip()
    if header.lower().startswith("bearer "):
        return header[7:].strip()
    return ""


class RateLimiter:
    """Thread-safe sliding-window limiter keyed by an arbitrary string."""

    def __init__(self, max_events: int, window_s: float = 60.0) -> None:
        self._max = max(1, int(max_events))
        self._window = float(window_s)
        self._hits: dict[str, list[float]] = {}
        self._lock = threading.Lock()

    def allow(self, key: str, cost: int = 1) -> bool:
        now = time.monotonic()
        with self._lock:
            hits = [t for t in self._hits.get(key, []) if now - t < self._window]
            if len(hits) + cost > self._max:
                self._hits[key] = hits
                return False
            hits.extend([now] * cost)
            self._hits[key] = hits
            return True
