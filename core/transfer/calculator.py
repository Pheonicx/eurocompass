"""
core/transfer/calculator.py

Deterministic transfer cost calculation (spec Ch.10.5, Ch.9.6).

Per CLAUDE.md: "Financial calculations must remain deterministic.
Artificial Intelligence may explain calculations. AI must never replace
financial arithmetic." Nothing in this file is probabilistic or
AI-generated — same inputs always produce the same output.

Base currency: all totals are expressed in BDT (Bangladeshi Taka), since
that's what a Bangladeshi student is actually paying with. This isn't
modeled as a Currency object (core.models.Currency is for currencies
*being purchased*, like EUR/USD) — BDT here is just the calculation's
unit of account.

Honesty about fees: as of Phase 4, EuroCompass does not yet collect real
fee data from any bank (checked — v1.0 never has). Rather than silently
treating "no fee data" as "zero fees" (which would be a confident-looking
number built on an unverified assumption — exactly what CLAUDE.md's
Validation principles warn against: "prefer false warnings over false
confidence"), every result explicitly reports fees_verified=False when no
fees were supplied, and the Recommendation layer (recommender.py) is
required to disclose that in its explanation.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from core.models import Fee, Observation


@dataclass(frozen=True)
class TransferCostBreakdown:
    """Every number that went into a transfer cost, kept visible rather
    than collapsed into a single opaque total (spec: "Show Every Cost")."""

    bank_id: str
    product_id: str
    currency: str
    requested_amount: float
    exchange_rate: float  # the sell rate used (bank sells foreign currency to the customer)
    gross_cost_bdt: float  # requested_amount * exchange_rate, before fees
    fees_applied: tuple[Fee, ...]
    fees_total_bdt: float
    total_cost_bdt: float  # gross_cost_bdt + fees_total_bdt
    fees_verified: bool  # True only if at least one fee was actually applied to the total (not just supplied) — a fee skipped for an unsupported currency does not count
    notes: tuple[str, ...] = field(default_factory=tuple)


def calculate_transfer_cost(
    observation: Observation,
    requested_amount: float,
    fees: tuple[Fee, ...] = (),
) -> TransferCostBreakdown:
    """
    Calculate the full BDT cost of buying `requested_amount` of
    `observation.currency` from `observation.bank_id`, at the observation's
    sell rate, plus any known fees.

    The sell rate is used (not buy) because a student sending money
    abroad is *buying* foreign currency from the bank — the bank sells it
    to them. This matches v1.0's existing calculator.py logic exactly
    (total_cost = sell_rate * amount), just generalized beyond EUR-only
    and extended with fee-awareness.
    """
    if requested_amount <= 0:
        raise ValueError(f"requested_amount must be positive, got {requested_amount}")

    gross_cost = observation.sell * requested_amount

    fees_total, applied, notes = _apply_fees(gross_cost, fees)

    return TransferCostBreakdown(
        bank_id=observation.bank_id,
        product_id=observation.product_id,
        currency=observation.currency,
        requested_amount=requested_amount,
        exchange_rate=observation.sell,
        gross_cost_bdt=round(gross_cost, 2),
        fees_applied=applied,
        fees_total_bdt=round(fees_total, 2),
        total_cost_bdt=round(gross_cost + fees_total, 2),
        fees_verified=len(applied) > 0,
        notes=notes,
    )


def _apply_fees(
    gross_cost_bdt: float, fees: tuple[Fee, ...]
) -> tuple[float, tuple[Fee, ...], tuple[str, ...]]:
    """
    Sums applicable fees against a gross BDT cost.

    - Flat fees must be stated in BDT to be summed directly; a flat fee
      in another currency is skipped with a note rather than silently
      guessed at (no currency conversion is performed for fees — that
      would require its own exchange rate and its own validation, which
      doesn't exist yet).
    - Percentage fees are taken as a percentage of the gross BDT cost,
      regardless of the currency field (a percentage doesn't need
      converting).
    """
    total = 0.0
    applied: list[Fee] = []
    notes: list[str] = []

    for fee in fees:
        if fee.is_percentage:
            amount = gross_cost_bdt * (fee.amount / 100.0)
            total += amount
            applied.append(fee)
        elif fee.currency == "BDT":
            total += fee.amount
            applied.append(fee)
        else:
            notes.append(
                f"Skipped fee '{fee.name}': stated in {fee.currency}, "
                f"which this calculator can't convert to BDT yet."
            )

    return total, tuple(applied), tuple(notes)
