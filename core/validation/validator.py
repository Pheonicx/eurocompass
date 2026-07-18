"""
core/validation/validator.py

Orchestrates the validation pipeline (spec Ch.7.3):

    structural -> business -> historical -> cross-field -> decision

Structural validation mostly already happened by the time an Observation
exists at all — core/models.py's Observation refuses to be constructed
with missing/impossible values. This module runs the checks that need
things the domain model doesn't have on its own: currency-specific
config (business rules) and prior history (historical validation).

Per CLAUDE.md: "Never bypass validation. Never recommend rejected
observations. Prefer false warnings over false confidence." — every
rejection here is logged with a specific, human-readable reason, and
nothing calling this module should ever use a rejected Observation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence

from core.config.loader import PlatformConfig
from core.logging_setup import get_logger, validation_rejected
from core.models import Observation
from core.validation.historical import check_against_recent_history
from core.validation.rules import check_business_rules, check_rate_date_not_future

logger = get_logger("validation")


@dataclass(frozen=True)
class ValidationResult:
    observation: Observation
    accepted: bool
    reason: Optional[str] = None


def validate(
    observation: Observation,
    config: PlatformConfig,
    recent_history: Sequence[Observation] = (),
) -> ValidationResult:
    """
    Run one observation through the full pipeline. Returns a
    ValidationResult — never raises for an ordinary validation failure
    (that's the whole point: a rejection is an expected, logged outcome,
    not an error).
    """
    currency = config.currencies.get(observation.currency)
    if currency is None:
        reason = f"currency '{observation.currency}' is not configured"
        validation_rejected(logger, observation.bank_id, reason)
        return ValidationResult(observation, accepted=False, reason=reason)

    reason = check_business_rules(observation, currency)
    if reason:
        validation_rejected(logger, observation.bank_id, reason)
        return ValidationResult(observation, accepted=False, reason=reason)

    reason = check_rate_date_not_future(observation)
    if reason:
        validation_rejected(logger, observation.bank_id, reason)
        return ValidationResult(observation, accepted=False, reason=reason)

    reason = check_against_recent_history(observation, recent_history)
    if reason:
        validation_rejected(logger, observation.bank_id, reason)
        return ValidationResult(observation, accepted=False, reason=reason)

    return ValidationResult(observation, accepted=True)
