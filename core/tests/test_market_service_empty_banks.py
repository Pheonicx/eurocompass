"""
core/tests/test_market_service_empty_banks.py

Regression test for services/calculator.py + services/market_service.py.

get_rates() returns None only when exports/latest.json doesn't exist at
all -- but if every bank collector fails in a cycle (already observed as
a real possibility this project has hit), data["banks"] can legitimately
be an empty list, which get_rates() happily returns as []. That's not
None, so recommend_bank()'s `if rates is None: return None` guard never
fires, and it proceeds to calculate_transfer_cost([], amount), which
unconditionally does `results[0]` on an empty list -- raising IndexError
instead of returning None the way callers (telegram_bot/bot.py's
/recommend handler) clearly expect.

bot.py's broad except Exception catches this, but it means the user gets
a generic "Could not calculate recommendation" instead of the accurate
"No market data available" message the code was clearly written to show
for exactly this situation -- masking the real cause instead of
explaining it (CLAUDE.md: "Explain before recommend").
"""

import json

import pytest

from services import market_service
from services.calculator import calculate_transfer_cost, get_best_bank


def test_calculate_transfer_cost_on_empty_banks_returns_empty_not_crash():
    # Previously raised IndexError on `results[0]`.
    assert calculate_transfer_cost([], 1000) == []


def test_get_best_bank_on_empty_results_returns_none_not_crash():
    # Previously raised IndexError on `results[0]`.
    assert get_best_bank([]) is None


def test_recommend_bank_returns_none_when_all_banks_failed(tmp_path, monkeypatch):
    export_file = tmp_path / "latest.json"
    export_file.write_text(json.dumps({"banks": [], "generated_at": "2026-07-28T09:00:00+06:00"}))

    monkeypatch.setattr(market_service, "EXPORT_FILE", export_file)

    # Previously raised IndexError instead of returning None.
    assert market_service.recommend_bank(1000) is None


def test_recommend_bank_still_works_normally(tmp_path, monkeypatch):
    export_file = tmp_path / "latest.json"
    export_file.write_text(
        json.dumps(
            {
                "banks": [
                    {"bank": "Sonali", "sell": 128.50},
                    {"bank": "BRAC", "sell": 129.00},
                ],
                "generated_at": "2026-07-28T09:00:00+06:00",
            }
        )
    )

    monkeypatch.setattr(market_service, "EXPORT_FILE", export_file)

    result = market_service.recommend_bank(1000)

    assert result is not None
    assert result["bank"] == "Sonali"
