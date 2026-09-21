from decimal import Decimal

import pytest

from minisweagent.repopilot.deepseek_provider import (
    BudgetGuard,
    DeepSeekBalanceError,
    MissingDeepSeekCredential,
    build_deepseek_model,
    fetch_cny_balance,
    parse_cny_balance,
)


def test_deepseek_model_requires_key_before_agent_run():
    with pytest.raises(MissingDeepSeekCredential, match="DEEPSEEK_API_KEY"):
        build_deepseek_model({})


def test_deepseek_model_is_bounded_and_never_serializes_key():
    model = build_deepseek_model({"DEEPSEEK_API_KEY": "test-only-deepseek-key"})

    assert model.config.model_name == "deepseek/deepseek-flash"
    assert model.config.model_kwargs == {
        "drop_params": True,
        "temperature": 0,
        "max_tokens": 2048,
        "timeout": 120,
        "num_retries": 2,
    }
    assert "test-only-deepseek-key" not in str(model.serialize())
    assert "api_key" not in model.config.model_kwargs


def test_parse_cny_balance_uses_total_available_cny_balance():
    balance = parse_cny_balance(
        {
            "is_available": True,
            "balance_infos": [
                {"currency": "USD", "total_balance": "1.23"},
                {"currency": "CNY", "total_balance": "10.00"},
            ],
        }
    )

    assert balance == Decimal("10.00")


def test_budget_guard_requires_full_pair_cost_and_preserves_reserve():
    guard = BudgetGuard(starting_balance=Decimal("10.00"), max_spend=Decimal("8.00"), reserve=Decimal("2.00"))

    assert guard.can_start_pair(current_balance=Decimal("9.00"), estimated_pair_cost=Decimal("2.00")) is True
    assert guard.can_start_pair(current_balance=Decimal("3.00"), estimated_pair_cost=Decimal("1.01")) is False
    assert guard.can_start_pair(current_balance=Decimal("2.00"), estimated_pair_cost=Decimal("0.01")) is False


def test_fetch_balance_uses_bearer_header_without_returning_or_storing_key():
    observed = {}

    class Response:
        status_code = 200

        def json(self):
            return {
                "is_available": True,
                "balance_infos": [{"currency": "CNY", "total_balance": "10.00"}],
            }

    def request(url, **kwargs):
        observed["url"] = url
        observed["kwargs"] = kwargs
        return Response()

    result = fetch_cny_balance({"DEEPSEEK_API_KEY": "test-only-secret"}, request=request)

    assert result == Decimal("10.00")
    assert observed["url"] == "https://api.deepseek.com/user/balance"
    assert observed["kwargs"]["headers"] == {"Authorization": "Bearer test-only-secret"}
    assert observed["kwargs"]["timeout"] == 20
    assert "test-only-secret" not in repr(result)


def test_fetch_balance_redacts_provider_error_body():
    class Response:
        status_code = 401
        text = "request rejected for secret test-only-secret"

    with pytest.raises(DeepSeekBalanceError, match="HTTP 401") as error:
        fetch_cny_balance(
            {"DEEPSEEK_API_KEY": "test-only-secret"},
            request=lambda *args, **kwargs: Response(),
        )

    assert "test-only-secret" not in str(error.value)
