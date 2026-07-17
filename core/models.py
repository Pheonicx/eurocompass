"""
core/models.py

Core domain models for EuroCompass v2.0.

These classes describe the *concepts* EuroCompass works with (banks,
currencies, products, exchange rates, fees, observations) independently
of how data is collected, stored, or displayed. See
EUROCOMPASS_SPECIFICATION.md, Chapter 5 ("Domain Model"), for the full
definitions these classes implement.

Design rules this file follows (from CLAUDE.md):
- Historical integrity: Observation is immutable once created.
- One source of truth: these models are shared by every interface
  (dashboard, Telegram bot, API) instead of being redefined per-interface.
- No magic numbers / no hidden assumptions: every field is explicit.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class Confidence(str, Enum):
    """
    How much the platform trusts a given observation.

    HIGH   - collected from an official API or an unambiguous, clean source.
    MEDIUM - collected from a PDF/HTML source that required parsing/guessing.
    LOW    - collected via a fallback method, or values look unusual
             without being implausible enough to reject outright.
    """

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class SourceType(str, Enum):
    """
    Where an observation's data came from.

    Ordering matches CLAUDE.md's preferred source order:
    API > PDF > HTML > OCR > OTHER.
    """

    API = "api"
    PDF = "pdf"
    HTML = "html"
    OCR = "ocr"
    OTHER = "other"


@dataclass(frozen=True)
class Currency:
    """A transferable currency. Codes should follow ISO 4217 (e.g. EUR, USD)."""

    code: str
    name: str

    def __post_init__(self) -> None:
        if len(self.code) != 3 or not self.code.isalpha():
            raise ValueError(
                f"Currency code must be a 3-letter ISO 4217 code, got: {self.code!r}"
            )
        # dataclass is frozen, so this is the sanctioned way to normalize a field
        object.__setattr__(self, "code", self.code.upper())


@dataclass(frozen=True)
class Product:
    """
    A specific banking product an exchange rate or fee can apply to.

    Examples: "TT" (telegraphic transfer), "Student File", "Cash".
    Products are first-class because the same bank can publish different
    rates for the same currency depending on the product (spec 5.3).
    """

    id: str
    name: str
    description: str = ""


@dataclass(frozen=True)
class Fee:
    """A single monetary charge that can apply during a transfer."""

    id: str
    name: str
    amount: float
    currency: str  # ISO 4217 code the fee itself is charged in
    is_percentage: bool = False  # True => `amount` is a % of the transfer, not a flat charge


@dataclass(frozen=True)
class Bank:
    """
    A financial institution, treated as a plugin (CLAUDE.md "Plugin Mindset").

    `collector` is the dotted import path of the module that knows how to
    fetch this bank's rates. The rest of the platform never needs to know
    *how* a bank's collector works internally — only that it exists and
    exposes a standard interface (see core/collectors/base.py).
    """

    id: str
    name: str
    currencies: tuple[str, ...] = field(default_factory=tuple)
    products: tuple[str, ...] = field(default_factory=tuple)
    collector: Optional[str] = None
    source_urls: dict[str, str] = field(default_factory=dict)
    source_type: str = "other"  # one of SourceType's values; kept as str so config stays plain data


@dataclass(frozen=True)
class Observation:
    """
    One successful collection of an exchange rate at a point in time.

    Per CLAUDE.md's "Historical Integrity" rule: once created, an
    Observation must never be edited or overwritten. A correction is a
    *new* Observation with a later `collected_at`, not a change to an old
    one. Nothing in this codebase should ever mutate an Observation's
    fields after construction — the frozen dataclass enforces this.
    """

    bank_id: str
    currency: str
    product_id: str
    buy: float
    sell: float
    collected_at: datetime
    source_type: SourceType
    confidence: Confidence
    rate_date: Optional[str] = None  # the date the bank itself published the rate for
    is_stale: bool = False  # True if rate_date is older than expected
    raw_source: Optional[str] = None  # URL or file the data came from, for auditability
    metadata: dict = field(default_factory=dict)  # e.g. {"student_rate": 130.5}

    def __post_init__(self) -> None:
        if self.buy <= 0 or self.sell <= 0:
            raise ValueError(
                f"Invalid observation for {self.bank_id}/{self.currency}: "
                f"buy/sell must be positive (buy={self.buy}, sell={self.sell})"
            )
        if self.sell < self.buy:
            raise ValueError(
                f"Invalid observation for {self.bank_id}/{self.currency}: "
                f"sell ({self.sell}) is lower than buy ({self.buy})"
            )

    @property
    def spread(self) -> float:
        return round(self.sell - self.buy, 6)


def utc_now() -> datetime:
    """Single source of truth for 'now', so every part of the platform agrees on time."""
    return datetime.now(timezone.utc)
