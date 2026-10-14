from __future__ import annotations

import re
from dataclasses import dataclass

# Patterns for common PII in LATAM documents. Applied to any text before it is
# handed to a model. Business tax ids required for matching are extracted
# separately by the deterministic parser and never sent to the model.
_PATTERNS = [
    ("EMAIL", re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")),
    ("PHONE", re.compile(r"\+?\d[\d\s().-]{7,}\d")),
    ("CURP", re.compile(r"\b[A-Z]{4}\d{6}[HM][A-Z]{5}\d{2}\b")),
    ("CPF", re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b")),
    ("CNPJ", re.compile(r"\b\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}\b")),
]


@dataclass
class RedactionResult:
    text: str
    count: int
    kinds: list[str]


def redact(text: str) -> RedactionResult:
    if not text:
        return RedactionResult(text="", count=0, kinds=[])

    kinds: list[str] = []
    total = 0
    redacted = text
    for label, pattern in _PATTERNS:
        matches = pattern.findall(redacted)
        if matches:
            kinds.append(label)
            total += len(matches)
            redacted = pattern.sub(f"[{label}]", redacted)
    return RedactionResult(text=redacted, count=total, kinds=sorted(set(kinds)))


_INJECTION_MARKERS = [
    "ignore previous",
    "ignora las instrucciones",
    "system prompt",
    "you are now",
    "actúa como",
    "jailbreak",
    "disregard",
]


def injection_suspected(text: str) -> bool:
    lowered = (text or "").lower()
    return any(marker in lowered for marker in _INJECTION_MARKERS)
