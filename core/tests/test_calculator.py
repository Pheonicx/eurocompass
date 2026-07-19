import pytest

from core.models import Confidence, Fee, Observation, SourceType, utc_now
from core.transfer.calculator import calculate_transfer_cost


def _obs(sell=142.0, buy=139.0, bank_id="BRAC", currency="EUR"):
    return Observation(
        bank_id=bank_id,
        currency=currency,
        product_id="TT",
        buy=buy,
        sell=sell,
        collected_at=utc_now(),
        source_type=SourceType.PDF,
        confidence=Confidence.HIGH,
    )


def test_gross_cost_uses_sell_rate():
    result = calculate_transfer_cost(_obs(sell=142.0), requested_amount=100)
    assert result.gross_cost_bdt == 14200.0
    assert result.total_cost_bdt == 14200.0  # no fees supplied


def test_no_fees_means_fees_not_verified():
    result = calculate_transfer_cost(_obs(), requested_amount=100)
    assert result.fees_verified is False
    assert result.fees_applied == ()
    assert result.fees_total_bdt == 0.0


def test_flat_bdt_fee_is_added():
    fee = Fee(id="swift", name="SWIFT charge", amount=1500.0, currency="BDT")
    result = calculate_transfer_cost(_obs(sell=142.0), requested_amount=100, fees=(fee,))
    assert result.fees_total_bdt == 1500.0
    assert result.total_cost_bdt == 14200.0 + 1500.0
    assert result.fees_verified is True
    assert fee in result.fees_applied


def test_percentage_fee_is_applied_to_gross_cost():
    fee = Fee(id="processing", name="Processing fee", amount=2.0, currency="BDT", is_percentage=True)
    result = calculate_transfer_cost(_obs(sell=142.0), requested_amount=100, fees=(fee,))
    # gross cost 14200, 2% of that = 284
    assert result.fees_total_bdt == pytest.approx(284.0)
    assert result.total_cost_bdt == pytest.approx(14200.0 + 284.0)


def test_fee_in_unsupported_currency_is_skipped_with_a_note():
    fee = Fee(id="weird", name="Odd fee", amount=5.0, currency="EUR")
    result = calculate_transfer_cost(_obs(), requested_amount=100, fees=(fee,))
    assert fee not in result.fees_applied
    assert result.fees_total_bdt == 0.0
    assert any("Odd fee" in note for note in result.notes)
    # A skipped flat fee alone doesn't count as "verified" fee data.
    assert result.fees_verified is False


def test_multiple_fees_combine():
    swift = Fee(id="swift", name="SWIFT", amount=1200.0, currency="BDT")
    vat = Fee(id="vat", name="VAT", amount=5.0, currency="BDT", is_percentage=True)
    result = calculate_transfer_cost(_obs(sell=142.0), requested_amount=100, fees=(swift, vat))
    expected_fees = 1200.0 + (14200.0 * 0.05)
    assert result.fees_total_bdt == pytest.approx(expected_fees)
    assert len(result.fees_applied) == 2


def test_rejects_non_positive_amount():
    with pytest.raises(ValueError):
        calculate_transfer_cost(_obs(), requested_amount=0)
    with pytest.raises(ValueError):
        calculate_transfer_cost(_obs(), requested_amount=-50)


def test_breakdown_preserves_bank_and_currency_identity():
    result = calculate_transfer_cost(_obs(bank_id="EBL", currency="USD"), requested_amount=500)
    assert result.bank_id == "EBL"
    assert result.currency == "USD"
    assert result.product_id == "TT"
    assert result.requested_amount == 500


def test_negative_fee_is_rejected_not_applied_as_a_discount():
    """
    Regression test: a fee is a charge, never a discount. A negative
    amount (almost certainly a data-entry sign error) must not silently
    reduce the total -- that could make a bank look artificially
    cheapest and corrupt the recommendation ranking.
    """
    bad_fee = Fee(id="oops", name="Mistyped fee", amount=-1500.0, currency="BDT")
    result = calculate_transfer_cost(_obs(sell=142.0), requested_amount=100, fees=(bad_fee,))

    assert bad_fee not in result.fees_applied
    assert result.fees_total_bdt == 0.0
    assert result.total_cost_bdt == result.gross_cost_bdt  # unaffected by the bad fee
    assert any("negative" in note for note in result.notes)
    assert result.fees_verified is False  # nothing legitimate was actually applied


def test_negative_percentage_fee_is_also_rejected():
    bad_fee = Fee(id="oops", name="Mistyped percent", amount=-5.0, currency="BDT", is_percentage=True)
    result = calculate_transfer_cost(_obs(sell=142.0), requested_amount=100, fees=(bad_fee,))
    assert result.fees_total_bdt == 0.0
    assert result.fees_verified is False


def test_total_cost_always_equals_the_sum_of_the_two_displayed_parts():
    """
    Regression test for a real (proven-reproducible-with-random-values)
    rounding inconsistency: total_cost_bdt must always exactly equal
    gross_cost_bdt + fees_total_bdt as displayed -- never off by a cent
    from independently rounding the raw, unrounded numbers.
    """
    fee = Fee(id="processing", name="Processing", amount=0.602, currency="BDT", is_percentage=True)
    flat = Fee(id="flat", name="Flat charge", amount=1206.70, currency="BDT")

    obs = _obs(sell=155.4456)
    result = calculate_transfer_cost(obs, requested_amount=8448.98, fees=(fee, flat))

    assert result.total_cost_bdt == round(result.gross_cost_bdt + result.fees_total_bdt, 2)
