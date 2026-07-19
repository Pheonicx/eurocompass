"""
core/transfer/recommender.py

The recommendation engine (spec Ch.9). Turns a set of per-bank transfer
cost breakdowns into a ranked recommendation with a mandatory,
human-readable explanation.

Per CLAUDE.md: "Always explain why a recommendation exists," and per the
spec's Explainability section (9.11), every recommendation must be able
to answer: why this bank, why not the others, which fees were
considered, how confident the platform is, and what's still unknown.
This module builds that explanation as plain text alongside the
recommendation — never leaves it for the caller to construct separately,
which is how explanations tend to quietly go missing over time.

Ranking is purely by core.transfer.calculator's deterministic
total_cost_bdt — no AI, no randomness, no hidden weighting.
"""

from __future__ import annotations

from dataclasses import dataclass

from core.models import Confidence, Observation
from core.transfer.calculator import TransferCostBreakdown

_CONFIDENCE_RANK = {Confidence.LOW: 0, Confidence.MEDIUM: 1, Confidence.HIGH: 2}


def _lower_confidence(a: Confidence, b: Confidence) -> Confidence:
    return a if _CONFIDENCE_RANK[a] <= _CONFIDENCE_RANK[b] else b


@dataclass(frozen=True)
class Alternative:
    bank_id: str
    total_cost_bdt: float
    extra_cost_vs_recommended_bdt: float
    fees_verified: bool


@dataclass(frozen=True)
class Recommendation:
    currency: str
    product_id: str
    requested_amount: float
    recommended_bank_id: str
    total_cost_bdt: float
    estimated_savings_vs_most_expensive_bdt: float
    confidence: Confidence
    explanation: str
    alternatives: tuple[Alternative, ...]
    breakdown: TransferCostBreakdown


def generate_recommendation(
    breakdowns: list[TransferCostBreakdown],
    observations_by_bank: dict[str, Observation],
    bank_names: dict[str, str] | None = None,
) -> Recommendation:
    """
    breakdowns: one TransferCostBreakdown per candidate bank (same
        currency/product/amount), from core.transfer.calculator.
    observations_by_bank: the Observation each breakdown was built from,
        keyed by bank_id — used to factor collection confidence into the
        recommendation's own confidence.
    bank_names: optional bank_id -> display name, for a nicer explanation.
        Falls back to the bank_id itself if not provided.
    """
    if not breakdowns:
        raise ValueError("generate_recommendation requires at least one breakdown")

    names = bank_names or {}

    ranked = sorted(breakdowns, key=lambda b: b.total_cost_bdt)
    best = ranked[0]
    worst = ranked[-1]

    savings = round(worst.total_cost_bdt - best.total_cost_bdt, 2)

    observation = observations_by_bank.get(best.bank_id)
    confidence = observation.confidence if observation else Confidence.LOW
    if not best.fees_verified:
        # Total cost is a lower bound (missing fees), so it can't be
        # presented with full confidence even if the exchange rate
        # itself was collected reliably.
        confidence = _lower_confidence(confidence, Confidence.MEDIUM)

    alternatives = tuple(
        Alternative(
            bank_id=b.bank_id,
            total_cost_bdt=b.total_cost_bdt,
            extra_cost_vs_recommended_bdt=round(b.total_cost_bdt - best.total_cost_bdt, 2),
            fees_verified=b.fees_verified,
        )
        for b in ranked[1:]
    )

    explanation = _build_explanation(best, ranked, names, observation, confidence)

    return Recommendation(
        currency=best.currency,
        product_id=best.product_id,
        requested_amount=best.requested_amount,
        recommended_bank_id=best.bank_id,
        total_cost_bdt=best.total_cost_bdt,
        estimated_savings_vs_most_expensive_bdt=savings,
        confidence=confidence,
        explanation=explanation,
        alternatives=alternatives,
        breakdown=best,
    )


def _bank_label(bank_id: str, names: dict[str, str]) -> str:
    return names.get(bank_id, bank_id)


def _build_explanation(
    best: TransferCostBreakdown,
    ranked: list[TransferCostBreakdown],
    names: dict[str, str],
    observation: Observation | None,
    confidence: Confidence,
) -> str:
    parts: list[str] = []

    best_label = _bank_label(best.bank_id, names)
    parts.append(
        f"{best_label} is recommended for {best.requested_amount:,.2f} {best.currency}: "
        f"total estimated cost of {best.total_cost_bdt:,.2f} BDT "
        f"(exchange rate {best.exchange_rate:.4f}, gross cost {best.gross_cost_bdt:,.2f} BDT"
        + (f", plus {best.fees_total_bdt:,.2f} BDT in known fees" if best.fees_verified else "")
        + ")."
    )

    if best.notes:
        parts.append("Note: " + " ".join(best.notes))

    if not best.fees_verified:
        parts.append(
            "No verified fee data (SWIFT charge, processing fee, VAT, etc.) is "
            "available yet for this bank, so this total reflects the exchange "
            "cost only — the real total may be somewhat higher once fees are added."
        )

    if len(ranked) > 1:
        runner_up = ranked[1]
        runner_label = _bank_label(runner_up.bank_id, names)
        gap = round(runner_up.total_cost_bdt - best.total_cost_bdt, 2)
        parts.append(
            f"The next-best option, {runner_label}, would cost {gap:,.2f} BDT more."
        )
        others = ", ".join(_bank_label(b.bank_id, names) for b in ranked[2:])
        if others:
            parts.append(f"Other options considered, in order: {others}.")

    if observation is not None and observation.is_stale:
        parts.append(
            "The underlying rate used for this recommendation is flagged as "
            "stale (older than expected) — treat this recommendation with "
            "extra caution until a fresher rate is collected."
        )

    parts.append(f"Overall confidence in this recommendation: {confidence.value}.")

    return " ".join(parts)
