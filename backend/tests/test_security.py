import base64
import os

import pytest
from starlette.testclient import TestClient

from app import config, db, security, seed
from app import main


@pytest.fixture(autouse=True)
def temp_db(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", os.path.join(str(tmp_path), "test.db"))
    monkeypatch.setattr(seed, "seed_if_empty", lambda: None)
    db.init_db()
    yield


def test_ssrf_blocks_metadata_schemes_and_empty():
    for url in ["http://169.254.169.254/latest/", "file:///etc/passwd", "ftp://x/y", ""]:
        with pytest.raises(security.UnsafeUrlError):
            security.validate_outbound_url(url)


def test_ssrf_allows_loopback_by_default():
    assert security.validate_outbound_url("http://127.0.0.1:8000/erp-web")


def test_ssrf_blocks_private_when_disallowed(monkeypatch):
    monkeypatch.setattr(config, "ALLOW_PRIVATE_NETWORKS", False)
    with pytest.raises(security.UnsafeUrlError):
        security.validate_outbound_url("http://10.0.0.5/x")
    with pytest.raises(security.UnsafeUrlError):
        security.validate_outbound_url("http://127.0.0.1/x")


def test_secret_encryption_roundtrip(monkeypatch):
    monkeypatch.setattr(config, "DB_ENCRYPTION_KEY", base64.b64encode(b"k" * 32).decode())
    enc = security.encrypt_secret("super-secret")
    assert security.is_encrypted(enc)
    assert security.decrypt_secret(enc) == "super-secret"
    assert not security.is_encrypted("plaintext")


def test_rate_limiter_window():
    limiter = security.RateLimiter(3, 60)
    assert [limiter.allow("c") for _ in range(5)] == [True, True, True, False, False]


def test_auth_middleware_requires_token_for_remote():
    token = security.load_or_create_token()
    with TestClient(main.app) as client:
        assert client.get("/api/health").status_code == 200
        assert client.get("/api/invoices").status_code == 401
        ok = client.get("/api/invoices", headers={"Authorization": f"Bearer {token}"})
        assert ok.status_code == 200


def test_auth_middleware_trusts_loopback(monkeypatch):
    monkeypatch.setattr(security, "is_loopback", lambda host: True)
    with TestClient(main.app) as client:
        assert client.get("/api/invoices").status_code == 200


def test_auth_can_be_disabled(monkeypatch):
    monkeypatch.setattr(config, "AUTH_ENABLED", False)
    with TestClient(main.app) as client:
        assert client.get("/api/invoices").status_code == 200
