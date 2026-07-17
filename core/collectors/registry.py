"""
core/collectors/registry.py

The single entry point for "go collect data from all configured banks."

This is what Phase 2+ code (validation, storage, the recommendation
engine, the dashboard, the Telegram bot) should import — never the
individual bank collector modules directly. That's what makes banks true
plugins: this file doesn't know or care whether a given bank's collector
is a legacy v1.0 module or a brand-new v2.0 one, and adding a new bank
never requires touching this file (CLAUDE.md: "Plugin Mindset").
"""

from __future__ import annotations

from core.collectors.base import Collector
from core.collectors.legacy_adapter import LegacyCollectorAdapter
from core.config.loader import PlatformConfig, load_config
from core.models import Observation

# All of v1.0's five collectors are legacy modules today, so this is the
# only adapter registered right now. When a bank gets a purpose-built v2.0
# collector, it gets its own entry here keyed by whatever identifies that
# collector "kind" — the config and registry design already support this
# without changes to how collect_all() works.
_DEFAULT_COLLECTOR: Collector = LegacyCollectorAdapter()


def collect_all(config: PlatformConfig | None = None) -> list[Observation]:
    """
    Run every configured bank's collector and return all Observations
    produced. A bank that fails contributes zero observations and is
    logged, but never stops the others (CLAUDE.md: "One failed bank
    should never stop the platform").
    """
    cfg = config or load_config()

    observations: list[Observation] = []
    for bank in cfg.banks.values():
        observations.extend(_DEFAULT_COLLECTOR.collect(bank))

    return observations


def collect_one(bank_id: str, config: PlatformConfig | None = None) -> list[Observation]:
    """Run a single bank's collector by id. Useful for testing/debugging one bank."""
    cfg = config or load_config()

    bank = cfg.banks.get(bank_id)
    if bank is None:
        raise KeyError(f"Unknown bank id: {bank_id!r}. Configured banks: {list(cfg.banks)}")

    return _DEFAULT_COLLECTOR.collect(bank)
