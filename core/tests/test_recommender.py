import pytest

from core.models import Confidence, Fee, Observation, SourceType, utc_now
from core.transfer.calculator import calculate_transfer_cost
from core.transfer.recommender import generate_recommendation


def _obs(bank_id, sell, confidence=Confidence.HIGH, is_stale=False):
    return Observation(
        bank_id=bank_id,
        currency="EUR",
        product_id="TT",
        buy=sell - 3,
        sell=sell,
        collected_at=utc_now(),
        source_type=SourceType.PDF,
        confidence=confidence,
        is_stale=is_stale,
    )


def _breakdowns_and_obs(bank_sells: dict, fees_by_bank=None, **kwargs):
    fees_by_bank = fees_by_bank or {}
    observations = {bank_id: _obs(bank_id, sell, **kwargs) for bank_id, sell in bank_sells.items()}
    breakdowns = [
        calculate_transfer_cost(obs, requested_amount=100, fees=fees_by_bank.get(bank_id, ()))
        for bank_id, obs in observations.items()
    ]
    return breakdowns, observations


def test_cheapest_bank_is_recommended():
    breakdowns, observations = _breakdowns_and_obs({"BRAC": 142.0, "CITY": 140.0, "EBL": 143.0})
    rec = generate_recommendation(breakdowns, observations)
    assert rec.recommended_bank_id == "CITY"
    assert rec.total_cost_bdt == 14000.0


def test_savings_is_versus_most_expensive():
    breakdowns, observations = _breakdowns_and_obs({"BRAC": 142.0, "CITY": 140.0, "EBL": 143.0})
    rec = generate_recommendation(breakdowns, observations)
    # cheapest 14000, most expensive 14300 -> savings of 300
    assert rec.estimated_savings_vs_most_expensive_bdt == pytest.approx(300.0)


def test_alternatives_are_sorted_and_exclude_the_winner():
    breakdowns, observations = _breakdowns_and_obs({"BRAC": 142.0, "CITY": 140.0, "EBL": 143.0})
    rec = generate_recommendation(breakdowns, observations)
    assert [a.bank_id for a in rec.alternatives] == ["BRAC", "EBL"]
    assert rec.alternatives[0].extra_cost_vs_recommended_bdt == pytest.approx(200.0)


def test_confidence_capped_when_fees_unverified():
    breakdowns, observations = _breakdowns_and_obs(
        {"CITY": 140.0}, confidence=Confidence.HIGH
    )
    rec = generate_recommendation(breakdowns, observations)
    # HIGH rate confidence, but no fees supplied -> capped at MEDIUM
    assert rec.confidence == Confidence.MEDIUM


def test_confidence_not_upgraded_by_verified_fees():
    fee = Fee(id="swift", name="SWIFT", amount=1000.0, currency="BDT")
    breakdowns, observations = _breakdowns_and_obs(
        {"CITY": 140.0}, fees_by_bank={"CITY": (fee,)}, confidence=Confidence.LOW
    )
    rec = generate_recommendation(breakdowns, observations)
    # LOW rate confidence stays LOW even with verified fees (never upgraded)
    assert rec.confidence == Confidence.LOW


def test_explanation_mentions_recommended_bank():
    breakdowns, observations = _breakdowns_and_obs({"BRAC": 142.0, "CITY": 140.0})
    rec = generate_recommendation(breakdowns, observations)
    assert "CITY" in rec.explanation


def test_explanation_discloses_unverified_fees():
    breakdowns, observations = _breakdowns_and_obs({"CITY": 140.0})
    rec = generate_recommendation(breakdowns, observations)
    assert "No verified fee data" in rec.explanation


def test_skipped_fee_notes_survive_even_when_no_fee_was_applied():
    """
    Regression test: notes explaining why a fee was skipped (e.g. a
    negative amount, or an unsupported currency) were previously dropped
    silently whenever fees_verified was False -- exactly the situation
    where that context matters most to a user trying to understand why
    the total looks the way it does.
    """
    from core.transfer.calculator import calculate_transfer_cost

    bad_fee = Fee(id="oops", name="Mistyped fee", amount=-500.0, currency="BDT")
    obs = _obs("CITY", 140.0)
    breakdown = calculate_transfer_cost(obs, requested_amount=100, fees=(bad_fee,))

    rec = generate_recommendation([breakdown], {"CITY": obs})

    assert breakdown.fees_verified is False
    assert "Mistyped fee" in rec.explanation
    assert "negative" in rec.explanation


def test_explanation_mentions_runner_up_gap():
    breakdowns, observations = _breakdowns_and_obs({"BRAC": 142.0, "CITY": 140.0})
    rec = generate_recommendation(breakdowns, observations)
    assert "BRAC" in rec.explanation
    assert "more" in rec.explanation


def test_explanation_warns_about_stale_rate():
    breakdowns, observations = _breakdowns_and_obs({"CITY": 140.0}, is_stale=True)
    rec = generate_recommendation(breakdowns, observations)
    assert "stale" in rec.explanation.lower()


def test_bank_names_are_used_in_explanation_when_provided():
    breakdowns, observations = _breakdowns_and_obs({"CITY": 140.0})
    rec = generate_recommendation(breakdowns, observations, bank_names={"CITY": "City Bank PLC"})
    assert "City Bank PLC" in rec.explanation


def test_requires_at_least_one_breakdown():
    with pytest.raises(ValueError):
        generate_recommendation([], {})
