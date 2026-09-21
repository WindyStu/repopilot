"""Credential-safe DeepSeek model and experiment budget primitives."""

from __future__ import annotations

import os
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any

import requests

from minisweagent.models.litellm_model import LitellmModel


class MissingDeepSeekCredential(RuntimeError):
    """Raised when DeepSeek is selected without a configured API key."""


class DeepSeekBalanceError(RuntimeError):
    """Raised when the balance endpoint cannot return a safe usable result."""


def build_deepseek_model(environ: Mapping[str, str] | None = None) -> LitellmModel:
    """Build the bounded experiment model without retaining its API key."""

    env = os.environ if environ is None else environ
    if not env.get("DEEPSEEK_API_KEY"):
        raise MissingDeepSeekCredential(
            "DEEPSEEK_API_KEY is required. Export it in the current shell before starting the experiment."
        )
    return LitellmModel(
        model_name="deepseek/deepseek-flash",
        cost_tracking="ignore_errors",
        model_kwargs={
            "drop_params": True,
            "temperature": 0,
            "max_tokens": 2048,
            "timeout": 120,
            "num_retries": 2,
        },
    )


def parse_cny_balance(payload: Mapping[str, Any]) -> Decimal:
    """Extract the available CNY balance from DeepSeek's balance response."""

    if not payload.get("is_available"):
        msg = "DeepSeek balance is not available"
        raise ValueError(msg)
    for balance in payload.get("balance_infos", []):
        if balance.get("currency") == "CNY":
            try:
                return Decimal(str(balance["total_balance"]))
            except (InvalidOperation, KeyError) as error:
                msg = "DeepSeek returned an invalid CNY balance"
                raise ValueError(msg) from error
    msg = "DeepSeek response did not include a CNY balance"
    raise ValueError(msg)


def fetch_cny_balance(
    environ: Mapping[str, str] | None = None,
    *,
    request: Callable[..., Any] = requests.get,
) -> Decimal:
    """Fetch the CNY balance without retaining credentials or provider bodies."""

    env = os.environ if environ is None else environ
    key = env.get("DEEPSEEK_API_KEY")
    if not key:
        raise MissingDeepSeekCredential("DEEPSEEK_API_KEY is required to query the DeepSeek balance.")
    try:
        response = request(
            "https://api.deepseek.com/user/balance",
            headers={"Authorization": f"Bearer {key}"},
            timeout=20,
        )
    except requests.RequestException as error:
        msg = f"DeepSeek balance request failed: {type(error).__name__}"
        raise DeepSeekBalanceError(msg) from error
    if response.status_code != 200:
        raise DeepSeekBalanceError(f"DeepSeek balance request failed with HTTP {response.status_code}")
    try:
        return parse_cny_balance(response.json())
    except (ValueError, TypeError) as error:
        raise DeepSeekBalanceError("DeepSeek balance response was invalid") from error


@dataclass(frozen=True)
class BudgetGuard:
    starting_balance: Decimal
    max_spend: Decimal
    reserve: Decimal

    def can_start_pair(self, *, current_balance: Decimal, estimated_pair_cost: Decimal) -> bool:
        """Return whether both halves of a pair fit the spend cap and reserve."""

        if estimated_pair_cost < 0:
            msg = "Estimated pair cost cannot be negative"
            raise ValueError(msg)
        spent = max(Decimal("0"), self.starting_balance - current_balance)
        return spent + estimated_pair_cost <= self.max_spend and current_balance - estimated_pair_cost >= self.reserve
