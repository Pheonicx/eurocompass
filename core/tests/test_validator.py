from core.config.loader import PlatformConfig
from core.models import Confidence, Currency, Observation, Product, SourceType, utc_now
from core.validation.validator import validate

CONFIG = PlatformConfig(
    currencies={
        "EUR": Currency(code="EUR", name="Euro", min_rate=120, max_rate=170, max_spread=10),
        "USD": Currency(code="USD", name="US Dollar", min_rate=100, max_rate=150, max_spread=8),
    },
    products={"TT": Product(id="TT", name="Telegraphic Transfer")},
    banks={},
)


def _obs(currency="EUR", buy=139.0, sell=None):
    return Observation(
        bank_id="BRAC",
        currency=currency,
        product_id="TT",
        buy=buy,
        sell=sell if sell is not None else buy + 3,
        collected_at=utc_now(),
        source_type=SourceType.PDF,
        confidence=Confidence.MEDIUM,
    )


def test_valid_observation_is_accepted():
    result = validate(_obs(), CONFIG)
    assert result.accepted is True
    assert result.reason is None


def test_unconfigured_currency_is_rejected():
    result = validate(_obs(currency="GBP"), CONFIG)
    assert result.accepted is False
    assert "not configured" in result.reason


def test_out_of_range_rate_is_rejected():
    result = validate(_obs(buy=50.0, sell=55.0), CONFIG)
    assert result.accepted is False


def test_historical_spike_is_rejected():
    recent = [_obs(buy=139.0)]
    result = validate(_obs(buy=159.0), CONFIG, recent_history=recent)
    assert result.accepted is False
    assert "%" in result.reason


def test_result_carries_the_original_observation():
    obs = _obs()
    result = validate(obs, CONFIG)
    assert result.observation is obs
