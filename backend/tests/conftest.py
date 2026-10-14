from __future__ import annotations

import pytest

from app import erp_config
from app.agent.erp import reset_backend


@pytest.fixture(autouse=True)
def _pin_erp_demo(monkeypatch):
    """Pin the ERP provider to `demo` for the whole suite.

    Without this, tests read the developer's real `backend/data/erp.json`, so a
    machine connected to a real ERP would fail the demo expectations (and vice
    versa). Tests that need another provider override `get_config` themselves.
    """
    monkeypatch.setattr(erp_config, "get_config", lambda: {"provider": "demo", "corebiz": {}})
    reset_backend()
    yield
    reset_backend()
