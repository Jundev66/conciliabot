from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
DB_PATH = DATA_DIR / "app.db"

# LLM gateway (optional). With no key configured the agent runs fully offline
# using the deterministic heuristic provider.
LLM_ENABLED = os.getenv("CONCILIABOT_LLM", "off").lower() in {"1", "on", "true", "yes"}
LLM_BASE_URL = os.getenv("CONCILIABOT_LLM_BASE_URL", "")
LLM_API_KEY = os.getenv("CONCILIABOT_LLM_API_KEY", "")
LLM_FALLBACK_BASE_URL = os.getenv("CONCILIABOT_LLM_FALLBACK_BASE_URL", "")
LLM_FALLBACK_API_KEY = os.getenv("CONCILIABOT_LLM_FALLBACK_API_KEY", "")

# Runtime budgets per pipeline execution.
BUDGET_MAX_TOKENS = int(os.getenv("CONCILIABOT_BUDGET_TOKENS", "8000"))
BUDGET_MAX_MS = int(os.getenv("CONCILIABOT_BUDGET_MS", "60000"))

# Local records store. Raw source documents are only persisted when an
# encryption key is configured (AES-256-GCM); otherwise we keep just the hash.
# Whatever is stored is purged after DOCUMENT_RETENTION_DAYS (data minimisation).
DB_ENCRYPTION_KEY = os.getenv("CONCILIABOT_DB_KEY", "")
DOCUMENT_RETENTION_DAYS = int(os.getenv("CONCILIABOT_DOCUMENT_RETENTION_DAYS", "90"))

# --- Local security controls ----------------------------------------------
def _flag(name: str, default: str) -> bool:
    return os.getenv(name, default).lower() in {"1", "on", "true", "yes"}


# Protect /api/*: local (loopback) callers are trusted; remote clients must
# present the local API token. Turn off only for throwaway dev.
AUTH_ENABLED = os.getenv("CONCILIABOT_AUTH", "on").lower() in {"1", "on", "true", "yes"}
AUTH_TOKEN = os.getenv("CONCILIABOT_AUTH_TOKEN", "")
AUTH_TOKEN_FILE = DATA_DIR / "api_token"

# SSRF policy: private/loopback targets are allowed by default (BYOC: the ERP
# often lives on the LAN); set to off to restrict outbound calls to public IPs.
ALLOW_PRIVATE_NETWORKS = os.getenv("CONCILIABOT_ALLOW_PRIVATE", "on").lower() in {
    "1",
    "on",
    "true",
    "yes",
}

# Demo ERP web mock. Disable in production so /erp-web/* is not exposed.
WEBMOCK_ENABLED = os.getenv("CONCILIABOT_WEBMOCK", "on").lower() in {"1", "on", "true", "yes"}

# Requests per minute allowed per client for outbound/costly endpoints.
RATE_LIMIT_PER_MIN = int(os.getenv("CONCILIABOT_RATE_LIMIT", "60"))

# Browser hardening. Both default to secure; opt out only if you must.
BROWSER_INSECURE = os.getenv("CONCILIABOT_BROWSER_INSECURE", "off").lower() in {
    "1",
    "on",
    "true",
    "yes",
}
BROWSER_NO_SANDBOX = os.getenv("CONCILIABOT_BROWSER_NO_SANDBOX", "off").lower() in {
    "1",
    "on",
    "true",
    "yes",
}

# ERP access. By default the agent talks to the real MCP server (spawned over
# stdio) and silently falls back to the in-process read-only sandbox if it is
# unavailable.
MCP_ENABLED = os.getenv("CONCILIABOT_MCP", "on").lower() in {"1", "on", "true", "yes"}

# Browser fallback (Playwright) for ERPs without an API. Read-only, opt-in per
# ingest request. ERP_WEB_URL is the template for the order page.
BROWSER_FALLBACK_ENABLED = os.getenv("CONCILIABOT_BROWSER", "on").lower() in {
    "1",
    "on",
    "true",
    "yes",
}
ERP_WEB_URL = os.getenv("CONCILIABOT_ERP_WEB_URL", "http://127.0.0.1:8000/erp-web/order/{number}")

# Local connection config (BYOC). Lives in backend/data/erp.json; secrets stay
# on the client machine and are never committed (data/ is gitignored).
ERP_CONFIG_PATH = DATA_DIR / "erp.json"

# Provider: "demo" (datos sinteticos + MCP) o "corebiz" (web del cliente).
ERP_PROVIDER = os.getenv("CONCILIABOT_ERP_PROVIDER", "demo").lower()

ERP_CONFIG_FILE = DATA_DIR / "erp.json"

# Corebiz (API REST NestJS). Auth: Authorization: Bearer <token>; x-corebiz-tenant
# selects the company when the token's user belongs to more than one.
COREBIZ_BASE_URL = os.getenv("COREBIZ_BASE_URL", "")
COREBIZ_API_KEY = os.getenv("COREBIZ_API_KEY", "")
COREBIZ_TENANT_ID = os.getenv("COREBIZ_TENANT_ID", "")
COREBIZ_TOKEN_HEADER = os.getenv("COREBIZ_TOKEN_HEADER", "Authorization")
COREBIZ_TOKEN_PREFIX = os.getenv("COREBIZ_TOKEN_PREFIX", "Bearer ")
COREBIZ_RECORDS_PATH = os.getenv("COREBIZ_RECORDS_PATH", "/v1/integrations/delivery-notes")

CORS_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:4173",
    "http://127.0.0.1:4173",
]
