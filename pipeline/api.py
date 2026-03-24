"""Shared Anthropic API caller with exponential backoff and token tracking."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from anthropic import Anthropic, APIError, APITimeoutError, RateLimitError

_MODEL = "claude-sonnet-4-20250514"

# Sonnet pricing per 1M tokens
_INPUT_COST_PER_M = 3.0
_OUTPUT_COST_PER_M = 15.0

_MAX_RETRIES = 3


@dataclass
class TokenUsage:
    """Accumulates token counts and cost across multiple API calls."""

    input_tokens: int = 0
    output_tokens: int = 0
    calls: int = 0

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens

    @property
    def estimated_cost_usd(self) -> float:
        input_cost = (self.input_tokens / 1_000_000) * _INPUT_COST_PER_M
        output_cost = (self.output_tokens / 1_000_000) * _OUTPUT_COST_PER_M
        return round(input_cost + output_cost, 4)

    def record(self, usage: Any) -> None:
        self.input_tokens += getattr(usage, "input_tokens", 0)
        self.output_tokens += getattr(usage, "output_tokens", 0)
        self.calls += 1


# Module-level accumulator — reset per pipeline run
_usage = TokenUsage()


def get_usage() -> TokenUsage:
    return _usage


def reset_usage() -> None:
    global _usage
    _usage = TokenUsage()


def call_claude(
    *,
    system: str,
    user_message: str,
    max_tokens: int = 2000,
) -> str:
    """Call Claude with exponential backoff retry on transient errors.

    Tracks token usage in the module-level accumulator.
    Returns the text content of the first response block.

    Also records per-call usage as (input_tokens, output_tokens) in
    the `last_call_usage` attribute for per-agent breakdown reporting.
    """
    client = Anthropic()
    last_exc: Exception | None = None

    for attempt in range(_MAX_RETRIES):
        try:
            response = client.messages.create(
                model=_MODEL,
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": user_message}],
            )
            _usage.record(response.usage)
            inp = getattr(response.usage, "input_tokens", 0)
            out = getattr(response.usage, "output_tokens", 0)
            call_claude.last_call_usage = (inp, out)
            return response.content[0].text.strip()

        except RateLimitError as exc:
            last_exc = exc
            wait = 2 ** attempt * 5
            print(f"Rate limited. Waiting {wait}s...")
            time.sleep(wait)

        except APITimeoutError as exc:
            last_exc = exc
            wait = 2 ** attempt * 3
            print(f"Timeout. Waiting {wait}s...")
            time.sleep(wait)

        except APIError as exc:
            if attempt == _MAX_RETRIES - 1:
                raise
            last_exc = exc
            wait = 2 ** attempt * 2
            print(f"API error: {exc}. Waiting {wait}s...")
            time.sleep(wait)

    raise RuntimeError(
        f"Claude API call failed after {_MAX_RETRIES} retries: {last_exc}"
    )


# Initialize the attribute
call_claude.last_call_usage = (0, 0)
