from __future__ import annotations

import hashlib
import json
from typing import Any

from . import config, security

# Local, per-install ERP connection settings. Secrets live only on the client
# machine (data/ is git-ignored). Environment variables seed the defaults; the
# file written from the UI takes precedence. The API key is encrypted at rest
# with AES-256-GCM when CONCILIABOT_DB_KEY is configured.


def _defaults() -> dict[str, Any]:
    return {
        "provider": config.ERP_PROVIDER,
        "corebiz": {
            "baseUrl": config.COREBIZ_BASE_URL,
            "apiKey": config.COREBIZ_API_KEY,
            "tenantId": config.COREBIZ_TENANT_ID,
            "tokenHeader": config.COREBIZ_TOKEN_HEADER,
            "tokenPrefix": config.COREBIZ_TOKEN_PREFIX,
            "recordsPath": config.COREBIZ_RECORDS_PATH,
        },
    }


def _merge(base: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _merge(merged[key], value)
        elif value is not None:
            merged[key] = value
    return merged


def _encrypt_secrets(cfg: dict[str, Any]) -> dict[str, Any]:
    corebiz = dict(cfg.get("corebiz") or {})
    key = corebiz.get("apiKey") or ""
    if key and not security.is_encrypted(key):
        corebiz["apiKey"] = security.encrypt_secret(key)
    return {**cfg, "corebiz": corebiz}


def _decrypt_secrets(cfg: dict[str, Any]) -> dict[str, Any]:
    corebiz = dict(cfg.get("corebiz") or {})
    key = corebiz.get("apiKey") or ""
    if security.is_encrypted(key):
        corebiz["apiKey"] = security.decrypt_secret(key)
    return {**cfg, "corebiz": corebiz}


def get_config() -> dict[str, Any]:
    data: dict[str, Any] = {}
    path = config.ERP_CONFIG_FILE
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            data = {}
    return _decrypt_secrets(_merge(_defaults(), data))


def save_config(patch: dict[str, Any]) -> dict[str, Any]:
    current = get_config()
    merged = _merge(current, patch)
    config.ERP_CONFIG_FILE.write_text(
        json.dumps(_encrypt_secrets(merged), indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return merged


def masked_config() -> dict[str, Any]:
    cfg = get_config()
    corebiz = dict(cfg.get("corebiz", {}))
    key = corebiz.get("apiKey") or ""
    corebiz["apiKey"] = f"***{key[-4:]}" if len(key) > 4 else ("***" if key else "")
    return {**cfg, "corebiz": corebiz}


def active_provider() -> str:
    return (get_config().get("provider") or "demo").lower()


def active_connection_id() -> str:
    """Stable id for the current ERP connection.

    Every record (transaction, audit, document) is tagged with this id so that
    data from different ERPs can never be mixed. The id is a non-reversible
    fingerprint of the connection target: changing the target yields a new id.
    """
    cfg = get_config()
    provider = (cfg.get("provider") or "demo").lower()
    if provider != "corebiz":
        return "demo"
    corebiz = cfg.get("corebiz") or {}
    material = f"{corebiz.get('baseUrl', '')}|{corebiz.get('tenantId', '')}"
    digest = hashlib.sha256(material.encode("utf-8")).hexdigest()[:12]
    return f"corebiz:{digest}"


def connection_meta() -> dict[str, str]:
    """Non-secret description of the active connection (never the API key)."""
    cfg = get_config()
    provider = (cfg.get("provider") or "demo").lower()
    corebiz = cfg.get("corebiz") or {}
    is_real = provider == "corebiz"
    return {
        "id": active_connection_id(),
        "erp_kind": provider,
        "base_url": (corebiz.get("baseUrl", "") if is_real else "sandbox"),
        "tenant_ref": (corebiz.get("tenantId", "") if is_real else ""),
    }
