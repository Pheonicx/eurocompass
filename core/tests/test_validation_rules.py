from datetime import datetime, timedelta, timezone

from core.models import Confidence, Currency, Observation, SourceType, utc_now
from core.validation.rules import check_business_rules, check_rate_date_not_future

EUR = Currency(code="EUR", name="Euro", min_rate=120, max_rate=170, max_spread=10)


def _obs(buy, sell, rate_date=None, collected_at=None):
    return Observation(
        bank_id="BRAC",
        currency="EUR",
        product_id="TT",
        buy=buy,
        sell=sell,
        collected_at=collected_at or utc_now(),
        source_type=SourceType.PDF,
        confidence=Confidence.MEDIUM,
        rate_date=rate_date,
    )


def test_plausible_rate_passes():
    assert check_business_rules(_obs(139.0, 142.0), EUR) is None


def test_rejects_buy_outside_range():
    reason = check_business_rules(_obs(50.0, 142.0), EUR)
    assert reason is not None
    assert "buy" in reason


def test_rejects_sell_outside_range():
    reason = check_business_rules(_obs(139.0, 500.0), EUR)
    assert reason is not None
    assert "sell" in reason


def test_rejects_spread_too_wide():
    reason = check_business_rules(_obs(130.0, 145.0), EUR)  # spread of 15 > max_spread 10
    assert reason is not None
    assert "spread" in reason


def test_rate_date_today_is_fine():
    today = utc_now()
    obs = _obs(139.0, 142.0, rate_date=today.date().isoformat(), collected_at=today)
    assert check_rate_date_not_future(obs) is None


def test_rate_date_in_future_is_rejected():
    now = utc_now()
    future = (now + timedelta(days=2)).date().isoformat()
    obs = _obs(139.0, 142.0, rate_date=future, collected_at=now)
    reason = check_rate_date_not_future(obs)
    assert reason is not None
    assert "future" in reason


def test_missing_rate_date_is_fine():
    assert check_rate_date_not_future(_obs(139.0, 142.0, rate_date=None)) is None


def test_malformed_rate_date_is_rejected():
    reason = check_rate_date_not_future(_obs(139.0, 142.0, rate_date="not-a-date"))
    assert reason is not None
