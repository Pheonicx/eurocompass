import pytest

from core.models import Confidence, Fee, Observation, SourceType, utc_now
from core.transfer.service import recommend_for_amount


def _obs(bank_id, sell, currency="EUR", product_id="TT"):
    return Observation(
        bank_id=bank_id,
        currency=currency,
        product_id=product_id,
        buy=sell - 3,
        sell=sell,
        collected_at=utc_now(),
        source_type=SourceType.PDF,
        confidence=Confidence.HIGH,
    )


def test_recommends_cheapest_across_real_observations():
    observations = [_obs("BRAC", 142.0), _obs("CITY", 140.0), _obs("EBL", 143.5)]
    rec = recommend_for_amount(observations, requested_amount=1000)
    assert rec.recommended_bank_id == "CITY"
    assert rec.total_cost_bdt == 140_000.0


def test_fees_by_bank_are_applied_per_bank():
    observations = [_obs("BRAC", 142.0), _obs("CITY", 140.0)]
    fees = {"CITY": (Fee(id="swift", name="SWIFT", amount=3000.0, currency="BDT"),)}
    rec = recommend_for_amount(observations, requested_amount=1000, fees_by_bank=fees)
    # CITY: 140,000 + 3,000 = 143,000 vs BRAC: 142,000 (no fees) -> BRAC now cheaper
    assert rec.recommended_bank_id == "BRAC"


def test_bank_names_pass_through():
    observations = [_obs("CITY", 140.0)]
    rec = recommend_for_amount(
        observations, requested_amount=100, bank_names={"CITY": "City Bank PLC"}
    )
    assert "City Bank PLC" in rec.explanation


def test_mismatched_currency_is_rejected():
    observations = [_obs("BRAC", 142.0, currency="EUR"), _obs("CITY", 118.0, currency="USD")]
    with pytest.raises(ValueError, match="currency"):
        recommend_for_amount(observations, requested_amount=100)


def test_mismatched_product_is_rejected():
    observations = [_obs("BRAC", 142.0, product_id="TT"), _obs("CITY", 140.0, product_id="STUDENT_FILE")]
    with pytest.raises(ValueError, match="product"):
        recommend_for_amount(observations, requested_amount=100)


def test_requires_at_least_one_observation():
    with pytest.raises(ValueError):
        recommend_for_amount([], requested_amount=100)


def test_duplicate_bank_id_is_rejected():
    """
    Regression test for a latent bug: passing the same bank twice would
    previously be silently accepted, with breakdowns and
    observations_by_bank disagreeing about which copy's data was used.
    """
    observations = [_obs("BRAC", 142.0), _obs("BRAC", 140.0)]
    with pytest.raises(ValueError, match="more than once"):
        recommend_for_amount(observations, requested_amount=100)
