from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from ..seed import (
    DOC_CFDI_APPROVED,
    DOC_CFDI_DISCREPANCY,
    DOC_CFDI_MATCH,
    DOC_DIAN_SCAN,
    DOC_NFE_DUPLICATE,
)

EXPECTED_STEPS = ["ingest", "preprocess", "classify", "extract", "fiscal", "match", "reconcile"]


@dataclass
class GoldenCase:
    id: str
    text: str
    filename: str
    source: str
    expected_status: str
    expected_format: str
    expect_duplicate: bool = False
    expect_fiscal: bool = True
    expect_discrepancy: bool = False
    expected_steps: list[str] = field(default_factory=lambda: list(EXPECTED_STEPS))


GOLDEN: list[GoldenCase] = [
    GoldenCase(
        id="cfdi_match",
        text=DOC_CFDI_MATCH,
        filename="A-45231.xml",
        source="email",
        expected_status="matched",
        expected_format="CFDI",
    ),
    GoldenCase(
        id="cfdi_discrepancy",
        text=DOC_CFDI_DISCREPANCY,
        filename="B-77810.xml",
        source="email",
        expected_status="discrepancy",
        expected_format="CFDI",
        expect_discrepancy=True,
        expect_fiscal=True,
    ),
    GoldenCase(
        id="nfe_duplicate",
        text=DOC_NFE_DUPLICATE,
        filename="NF-0099231.xml",
        source="api",
        expected_status="duplicate",
        expected_format="NF-e",
        expect_duplicate=True,
        expect_discrepancy=True,
    ),
    GoldenCase(
        id="dian_scan",
        text=DOC_DIAN_SCAN,
        filename="FE-2026-88431.pdf",
        source="carpeta",
        expected_status="needs_review",
        expected_format="PDF",
        expect_fiscal=True,
        expect_discrepancy=True,
    ),
    GoldenCase(
        id="cfdi_approved",
        text=DOC_CFDI_APPROVED,
        filename="A-45180.xml",
        source="email",
        expected_status="matched",
        expected_format="CFDI",
    ),
]


def evaluate_thresholds(metrics: dict[str, float]) -> tuple[bool, dict[str, float]]:
    thresholds = {
        "status_accuracy": 0.8,
        "format_accuracy": 0.9,
        "fiscal_accuracy": 0.9,
        "duplicate_recall": 1.0,
        "trajectory_pass_rate": 1.0,
    }
    passed = all(metrics.get(k, 0) >= v for k, v in thresholds.items())
    return passed, thresholds
