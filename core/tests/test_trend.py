from core.forecasting.trend import describe_trend, summarize_trend
from core.models import Confidence, Observation, SourceType, utc_now


def _obs(sell):
    return Observation(
        bank_id="BRAC",
        currency="EUR",
        product_id="TT",
        buy=sell - 3,
        sell=sell,
        collected_at=utc_now(),
        source_type=SourceType.PDF,
        confidence=Confidence.HIGH,
    )


def test_no_trend_with_fewer_than_two_observations():
    assert summarize_trend([]) is None
    assert summarize_trend([_obs(140.0)]) is None


def test_rising_trend_detected():
    trend = summarize_trend([_obs(140.0), _obs(142.0), _obs(145.0)])
    assert trend.direction == "rising"
    assert trend.change_pct > 0


def test_falling_trend_detected():
    trend = summarize_trend([_obs(145.0), _obs(142.0), _obs(140.0)])
    assert trend.direction == "falling"
    assert trend.change_pct < 0


def test_tiny_change_reported_as_stable():
    trend = summarize_trend([_obs(140.0), _obs(140.2)])  # ~0.14%, under the 0.5% threshold
    assert trend.direction == "stable"


def test_average_min_max_are_correct():
    trend = summarize_trend([_obs(140.0), _obs(150.0), _obs(145.0)])
    assert trend.average_sell == 145.0
    assert trend.lowest_sell == 140.0
    assert trend.highest_sell == 150.0
    assert trend.sample_size == 3


def test_volatility_is_zero_for_constant_rates():
    trend = summarize_trend([_obs(140.0), _obs(140.0), _obs(140.0)])
    assert trend.volatility == 0.0


def test_volatility_is_positive_for_varying_rates():
    trend = summarize_trend([_obs(138.0), _obs(142.0), _obs(140.0)])
    assert trend.volatility > 0


def test_describe_trend_mentions_bank_and_direction():
    trend = summarize_trend([_obs(140.0), _obs(145.0)])
    text = describe_trend(trend)
    assert "BRAC" in text
    assert "risen" in text
