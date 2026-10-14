from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass
from typing import Optional

from .. import config, security
from ..models import ModelTier


class BudgetExceeded(Exception):
    pass


@dataclass
class RunContext:
    """Tracks the per-execution token/time budget (runtimes)."""

    max_tokens: int = config.BUDGET_MAX_TOKENS
    max_ms: int = config.BUDGET_MAX_MS
    tokens_used: int = 0
    cache_hits: int = 0
    started: float = 0.0
    connection_id: str = "default"

    def __post_init__(self) -> None:
        self.started = time.perf_counter()

    def elapsed_ms(self) -> int:
        return int((time.perf_counter() - self.started) * 1000)

    def guard(self) -> None:
        if self.tokens_used >= self.max_tokens:
            raise BudgetExceeded(f"presupuesto de tokens agotado ({self.max_tokens})")
        if self.elapsed_ms() >= self.max_ms:
            raise BudgetExceeded(f"presupuesto de tiempo agotado ({self.max_ms} ms)")


@dataclass
class Completion:
    text: str
    tokens: int
    model: str
    cached: bool
    provider: str


def classify_difficulty(text: str, structured: bool) -> str:
    """Cheap heuristic used to route between the small and reasoning tiers."""
    if not structured and len(text) > 2500:
        return "hard"
    if any(word in (text or "").lower() for word in ("duda", "ambig", "inconsist", "parcial")):
        return "hard"
    return "easy"


class LLMGateway:
    """Single choke point for every model call.

    Provides model routing, token/time budgets, caching of repeated queries,
    retries with backoff and a fallback provider. With no provider configured
    it runs fully offline through the deterministic heuristic provider.
    """

    # Class-level so repeated queries are cached across runs, but every key is
    # namespaced by connection_id: prompts from different ERPs never mix.
    _cache: dict[str, Completion] = {}

    def __init__(self, ctx: RunContext) -> None:
        self.ctx = ctx

    @classmethod
    def clear_cache(cls) -> None:
        cls._cache.clear()

    def route(self, difficulty: str) -> ModelTier:
        return ModelTier.reasoning if difficulty == "hard" else ModelTier.small

    def complete(self, prompt: str, tier: ModelTier, label: str = "task") -> Completion:
        self.ctx.guard()

        namespace = self.ctx.connection_id or "default"
        key = hashlib.sha256(f"{namespace}|{tier.value}|{prompt}".encode()).hexdigest()
        cached = self._cache.get(key)
        if cached is not None:
            self.ctx.cache_hits += 1
            return Completion(cached.text, cached.tokens, cached.model, True, cached.provider)

        result = self._with_retry(prompt, tier, label)
        self._cache[key] = result
        self.ctx.tokens_used += result.tokens
        return result

    def _with_retry(self, prompt: str, tier: ModelTier, label: str, attempts: int = 3) -> Completion:
        last_error: Optional[Exception] = None
        for attempt in range(attempts):
            try:
                return self._primary(prompt, tier, label)
            except Exception as exc:  # noqa: BLE001 - retried with backoff
                last_error = exc
                if attempt < attempts - 1:
                    time.sleep(0.2 * (2**attempt))
        return self._fallback(prompt, tier, label, last_error)

    def _primary(self, prompt: str, tier: ModelTier, label: str) -> Completion:
        if not config.LLM_ENABLED:
            return self._heuristic(prompt, tier, label)
        return self._http(config.LLM_BASE_URL, config.LLM_API_KEY, prompt, tier, label)

    def _fallback(
        self, prompt: str, tier: ModelTier, label: str, error: Optional[Exception]
    ) -> Completion:
        if config.LLM_ENABLED and config.LLM_FALLBACK_BASE_URL:
            try:
                return self._http(
                    config.LLM_FALLBACK_BASE_URL, config.LLM_FALLBACK_API_KEY, prompt, tier, label
                )
            except Exception:  # noqa: BLE001
                pass
        result = self._heuristic(prompt, tier, label)
        return Completion(result.text, result.tokens, result.model, False, "heuristic-fallback")

    def _heuristic(self, prompt: str, tier: ModelTier, label: str) -> Completion:
        tokens = max(1, len(prompt) // 4)
        text = f"[{label}] analisis deterministico ({tier.value})."
        return Completion(text, tokens, f"heuristic-{tier.value}", False, "heuristic")

    def _http(self, base_url: str, api_key: str, prompt: str, tier: ModelTier, label: str) -> Completion:
        import httpx

        if not base_url:
            raise ValueError("LLM base_url vacia (CONCILIABOT_LLM_BASE_URL)")
        url = security.validate_outbound_url(
            f"{base_url.rstrip('/')}/chat/completions", purpose="llm"
        )
        model = "small-model" if tier == ModelTier.small else "reasoning-model"
        resp = httpx.post(
            url,
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0,
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        text = data["choices"][0]["message"]["content"]
        tokens = int(data.get("usage", {}).get("total_tokens", max(1, len(prompt) // 4)))
        return Completion(text, tokens, model, False, "primary")
