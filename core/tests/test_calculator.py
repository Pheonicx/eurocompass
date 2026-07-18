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
