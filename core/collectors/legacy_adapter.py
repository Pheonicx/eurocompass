"""
core/collectors/legacy_adapter.py

Wraps a v1.0 collector module (collectors/brac.py, collectors/city.py, ...)
so it satisfies the new Collector interface (core/collectors/base.py).

Important: this file does NOT re-implement or modify any bank's scraping
or PDF-parsing logic. It imports the existing collector module exactly as
main.py already does, calls its existing get_rate() function, and
translates the dict it returns into an Observation. If a bank's scraping
breaks or a bank's rate format changes, the fix belongs in that bank's own
file under collectors/ — never here (CLAUDE.md: "Never allow one bank's
implementation to influence another").
"""

from __future__ import annotations

import importlib

from core.logging_setup import (
    collection_completed,
    collection_started,
    collector_crashed,
    download_failure,
    get_logger,
)
from core.models import Bank, Confidence, Observation, SourceType, utc_now

logger = get_logger("collectors.legacy_adapter")


class LegacyCollectorAdapter:
    """
    Collector implementation that delegates to an existing v1.0 collector
    module. One instance can be reused for any bank whose config points at
    a legacy module via the "collector" field in banks.json.
    """

    def collect(self, bank: Bank) -> list[Observation]:
        collection_started(logger, bank.id)

        if not bank.collector:
            download_failure(logger, bank.id, "no collector module configured for this bank")
            return []

        try:
            module = importlib.import_module(bank.collector)
        except ImportError as e:
            download_failure(logger, bank.id, f"could not import {bank.collector}: {e}")
            return []

        if not hasattr(module, "get_rate"):
            download_failure(
                logger, bank.id, f"{bank.collector} has no get_rate() function"
            )
            return []

        try:
            raw = module.get_rate()
        except Exception as e:  # noqa: BLE001 - a crashing collector must not take down collection
            collector_crashed(logger, bank.id, e)
            return []

        if raw is None:
            download_failure(logger, bank.id, "collector returned no data")
            return []

        observation = self._to_observation(bank, raw)

        if observation is None:
            collection_completed(logger, bank.id, 0)
            return []

        collection_completed(logger, bank.id, 1)
        return [observation]

    def _to_observation(self, bank: Bank, raw: dict) -> Observation | None:
        """
        Translate a legacy collector's dict (as returned by get_rate(), e.g.
        {"bank": "BRAC", "currency": "EUR", "buy": ..., "sell": ..., ...})
        into an Observation. Returns None (and logs) if the dict is missing
        fields an Observation requires.
        """
        currency = raw.get("currency")
        buy = raw.get("buy")
        sell = raw.get("sell")

        if currency is None or buy is None or sell is None:
            download_failure(
                logger,
                bank.id,
                f"collector result missing currency/buy/sell: {raw!r}",
            )
            return None

        product_id = bank.products[0] if bank.products else "TT"

        try:
            source_type = SourceType(bank.source_type)
        except ValueError:
            source_type = SourceType.OTHER

        # A rate flagged stale, or one that only came from a fallback method,
        # is worth trusting less than a fresh primary-method rate. This is a
        # simple starting rule — Phase 3 (Validation) will make confidence
        # scoring more rigorous.
        confidence = Confidence.MEDIUM
        if raw.get("is_stale"):
            confidence = Confidence.LOW

        metadata = {}
        if raw.get("student") is not None:
            metadata["student_rate"] = raw["student"]

        try:
            return Observation(
                bank_id=bank.id,
                currency=currency,
                product_id=product_id,
                buy=float(buy),
                sell=float(sell),
                collected_at=utc_now(),
                source_type=source_type,
                confidence=confidence,
                rate_date=raw.get("rate_date"),
                is_stale=bool(raw.get("is_stale", False)),
                raw_source=bank.source_urls.get(currency),
                metadata=metadata,
            )
        except ValueError as e:
            # Observation.__post_init__ rejects impossible values (e.g. sell
            # < buy, negative rates) — surface that as a normal collection
            # failure rather than letting it crash the whole run.
            download_failure(logger, bank.id, f"collector produced an invalid rate: {e}")
            return None
