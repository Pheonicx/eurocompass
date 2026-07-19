"""
core/export.py

Builds the JSON snapshot a dashboard (or any other interface) reads.

This follows v1.0's own pattern exactly (services/market_service.py +
exports/latest.json): Python computes once, writes a plain JSON file,
a static frontend reads it — no live backend, no server costs. Written
to a NEW file (v2_exports/latest.json) so v1.0's own export is completely
untouched.

Combines:
- the most recent validated observation per bank, for each configured
  currency/product (from core.storage)
- a recommendation for a few representative transfer amounts, using
  core.transfer.service — so the dashboard can show a real, explained
  recommendation, not just a raw rate table
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from core.config.loader import PlatformConfig, load_config
from core.forecasting.trend import summarize_trend, describe_trend
from core.logging_setup import get_logger
from core.models import Observation, utc_now
from core.storage import observation_store
from core.storage.observation_store import DEFAULT_STORAGE_DIR
from core.transfer.service import recommend_for_amount

logger = get_logger("export")

DEFAULT_EXPORT_PATH = Path("v2_exports/latest.json")

# Representative amounts for the dashboard's example recommendations.
# 12,208 EUR matches the spec's own worked example (Appendix A, Workflow
# 1: Blocked Account Funding for Germany); 1,000 EUR/USD are smaller,
# more everyday amounts.
DEFAULT_SCENARIOS: tuple[tuple[str, str, float], ...] = (
    ("EUR", "TT", 1000.0),
    ("EUR", "TT", 12208.0),
    ("USD", "TT", 1000.0),
)


def _latest_observation_per_bank(
    bank_ids: Iterable[str], currency: str, product_id: str, storage_dir: Path
) -> list[Observation]:
    observations = []
    for bank_id in bank_ids:
        recent = observation_store.load_recent(
            bank_id, currency, product_id, limit=1, storage_dir=storage_dir
        )
        if recent:
            observations.append(recent[0])
    return observations


def build_export(
    config: PlatformConfig | None = None,
    storage_dir: Path = DEFAULT_STORAGE_DIR,
    scenarios: tuple[tuple[str, str, float], ...] = DEFAULT_SCENARIOS,
) -> dict:
    """
    Returns a plain dict, ready for json.dumps(). Kept separate from
    write_export() so tests (and future callers) can inspect the data
    without touching the filesystem.
    """
    cfg = config or load_config()
    bank_names = {b.id: b.name for b in cfg.banks.values()}

    rates_by_currency: dict[str, list[dict]] = {}
    trends_by_currency: dict[str, list[dict]] = {}
    recommendations: list[dict] = []

    for currency, product_id, amount in scenarios:
        observations = _latest_observation_per_bank(
            cfg.banks.keys(), currency, product_id, storage_dir
        )
        if not observations:
            logger.info(
                "EXPORT_SCENARIO_SKIPPED currency=%s product=%s reason=no_data",
                currency,
                product_id,
            )
            continue

        if currency not in rates_by_currency:
            rates_by_currency[currency] = [
                {
                    "bank_id": o.bank_id,
                    "bank_name": bank_names.get(o.bank_id, o.bank_id),
                    "buy": o.buy,
                    "sell": o.sell,
                    "confidence": o.confidence.value,
                    "is_stale": o.is_stale,
                    "collected_at": o.collected_at.isoformat(),
                }
                for o in sorted(observations, key=lambda o: o.sell)
            ]

        if currency not in trends_by_currency:
            trends_by_currency[currency] = _build_trends(
                cfg.banks.keys(), currency, product_id, storage_dir, bank_names
            )

        rec = recommend_for_amount(observations, amount, bank_names=bank_names)

        recommendations.append(
            {
                "currency": rec.currency,
                "product_id": rec.product_id,
                "requested_amount": rec.requested_amount,
                "recommended_bank_id": rec.recommended_bank_id,
                "recommended_bank_name": bank_names.get(
                    rec.recommended_bank_id, rec.recommended_bank_id
                ),
                "total_cost_bdt": rec.total_cost_bdt,
                "estimated_savings_vs_most_expensive_bdt": rec.estimated_savings_vs_most_expensive_bdt,
                "confidence": rec.confidence.value,
                "explanation": rec.explanation,
                "alternatives": [
                    {
                        "bank_id": a.bank_id,
                        "bank_name": bank_names.get(a.bank_id, a.bank_id),
                        "total_cost_bdt": a.total_cost_bdt,
                        "extra_cost_vs_recommended_bdt": a.extra_cost_vs_recommended_bdt,
                        "fees_verified": a.fees_verified,
                    }
                    for a in rec.alternatives
                ],
            }
        )

    return {
        "generated_at": utc_now().isoformat(),
        "rates_by_currency": rates_by_currency,
        "trends_by_currency": trends_by_currency,
        "recommendations": recommendations,
    }


def _build_trends(
    bank_ids, currency: str, product_id: str, storage_dir: Path, bank_names: dict[str, str]
) -> list[dict]:
    """
    One trend summary per bank that has at least 2 stored observations
    for this currency/product. Banks with fewer are simply omitted —
    not reported as "stable" or given a fabricated trend, since there's
    genuinely nothing yet to base one on (spec: "unknown information
    should remain unknown").
    """
    trends = []
    for bank_id in bank_ids:
        history = [
            o
            for o in observation_store.load_all(bank_id, storage_dir)
            if o.currency == currency and o.product_id == product_id
        ]

        trend = summarize_trend(history)
        if trend is None:
            continue

        trends.append(
            {
                "bank_id": trend.bank_id,
                "bank_name": bank_names.get(trend.bank_id, trend.bank_id),
                "sample_size": trend.sample_size,
                "average_sell": trend.average_sell,
                "lowest_sell": trend.lowest_sell,
                "highest_sell": trend.highest_sell,
                "volatility": trend.volatility,
                "direction": trend.direction,
                "change_pct": trend.change_pct,
                "description": describe_trend(trend),
            }
        )
    return trends


def write_export(
    config: PlatformConfig | None = None,
    storage_dir: Path = DEFAULT_STORAGE_DIR,
    export_path: Path = DEFAULT_EXPORT_PATH,
    scenarios: tuple[tuple[str, str, float], ...] = DEFAULT_SCENARIOS,
) -> Path:
    """Builds the export and writes it to disk as pretty-printed JSON."""
    data = build_export(config, storage_dir, scenarios)

    export_path.parent.mkdir(parents=True, exist_ok=True)
    export_path.write_text(json.dumps(data, indent=2))

    logger.info(
        "EXPORT_WRITTEN path=%s currencies=%d recommendations=%d",
        export_path,
        len(data["rates_by_currency"]),
        len(data["recommendations"]),
    )
    return export_path
