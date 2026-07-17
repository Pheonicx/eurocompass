"""
core/collectors/base.py

The plugin contract for bank collectors.

Anything that can produce a list of core.models.Observation objects for a
Bank counts as a collector, regardless of whether it's a brand-new v2.0
collector or an old v1.0 one wrapped by legacy_adapter.py. Downstream code
(the registry, validation, storage) only ever depends on this interface —
never on any specific bank's internals (CLAUDE.md: "Never allow one bank's
implementation to influence another").
"""

from __future__ import annotations

from typing import Protocol

from core.models import Bank, Observation


class Collector(Protocol):
    """
    A collector turns a Bank's configuration into zero or more Observations.

    Implementations must NOT raise on ordinary failure (a bank's site being
    down, a PDF failing to parse, etc.) — they should catch that themselves
    and return an empty list, logging what went wrong. Raising should be
    reserved for genuine programming errors. This mirrors CLAUDE.md's
    failure-handling rule: one bank failing must never stop the platform.
    """

    def collect(self, bank: Bank) -> list[Observation]:
        ...
