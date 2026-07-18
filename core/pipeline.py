"""
core/pipeline.py

The full v2.0 knowledge-acquisition pipeline, end to end (spec Ch.6.4):

    collect -> validate -> store

This is the one function a scheduler will eventually call on a timer,
replacing/extending v1.0's hourly GitHub Action. It does NOT run
automatically yet — nothing currently invokes run_collection_cycle() on
a schedule. Wiring that up is a deliberate future decision (tracked in
V2_PROGRESS.md), not something that should happen silently as a side
effect of adding this file.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from core.collectors.registry import collect_all
from core.config.loader import PlatformConfig, load_config
from core.logging_setup import get_logger
from core.storage import observation_store
from core.storage.observation_store import DEFAULT_STORAGE_DIR
from core.validation.validator import validate

logger = get_logger("pipeline")


@dataclass
class CycleSummary:
    collected: int
    accepted: int
    rejected: int
    rejections: list[tuple[str, str]] = field(default_factory=list)  # (bank_id, reason)


def run_collection_cycle(
    config: PlatformConfig | None = None,
    storage_dir: Path = DEFAULT_STORAGE_DIR,
) -> CycleSummary:
    """
    Run one full cycle: collect from every configured bank, validate
    each observation, and permanently store the ones that pass.
    Rejected observations are logged (validation_rejected) but not
    stored and never reach downstream systems — per CLAUDE.md, "never
    recommend rejected observations."
    """
    cfg = config or load_config()

    observations = collect_all(cfg)

    accepted = 0
    rejected = 0
    rejections: list[tuple[str, str]] = []

    for observation in observations:
        recent = observation_store.load_recent(
            observation.bank_id,
            observation.currency,
            observation.product_id,
            storage_dir=storage_dir,
        )
        result = validate(observation, cfg, recent_history=recent)

        if result.accepted:
            observation_store.append(observation, storage_dir=storage_dir)
            accepted += 1
        else:
            rejected += 1
            rejections.append((observation.bank_id, result.reason or "unknown reason"))

    logger.info(
        "CYCLE_COMPLETE collected=%d accepted=%d rejected=%d",
        len(observations),
        accepted,
        rejected,
    )

    return CycleSummary(
        collected=len(observations),
        accepted=accepted,
        rejected=rejected,
        rejections=rejections,
    )
