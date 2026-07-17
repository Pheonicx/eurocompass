"""
core/logging_setup.py

Central logging for EuroCompass v2.0.

CLAUDE.md requires that important events always be logged, specifically:
collection started, collection completed, download failure, parser
failure, validation rejection, recommendation generated, and unexpected
values. This module provides one logger and one small set of event
functions so every future component (collectors, validators, the
recommendation engine, interfaces) logs those events the same way,
instead of every module inventing its own log message format.

This does not replace utils/logger.py, which v1.0's main.py still uses —
it's a new, separate logger for v2.0 code so nothing about v1.0's running
behaviour changes.
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

_LOG_FILE = LOG_DIR / f"v2-{datetime.now().strftime('%Y-%m-%d')}.log"

_handler = logging.FileHandler(_LOG_FILE)
_handler.setFormatter(
    logging.Formatter("%(asctime)s | %(levelname)-8s | %(name)s | %(message)s")
)

_console_handler = logging.StreamHandler()
_console_handler.setFormatter(logging.Formatter("%(levelname)-8s | %(message)s"))

_logger = logging.getLogger("eurocompass.v2")
_logger.setLevel(logging.INFO)
if not _logger.handlers:
    _logger.addHandler(_handler)
    _logger.addHandler(_console_handler)


def get_logger(component: str) -> logging.Logger:
    """
    Get a logger for a specific component, e.g. get_logger('collectors.brac').
    All output still goes to the same v2 log file, just tagged by component.
    """
    return _logger.getChild(component)


# --- Structured event helpers -----------------------------------------
# Thin wrappers so every component logs these specific, required events
# (CLAUDE.md "Logging") the same way, with the same fields, instead of
# free-text messages that are hard to search later.

def collection_started(logger: logging.Logger, bank_id: str) -> None:
    logger.info("COLLECTION_STARTED bank=%s", bank_id)


def collection_completed(logger: logging.Logger, bank_id: str, count: int) -> None:
    logger.info("COLLECTION_COMPLETED bank=%s observations=%d", bank_id, count)


def download_failure(logger: logging.Logger, bank_id: str, reason: str) -> None:
    logger.warning("DOWNLOAD_FAILURE bank=%s reason=%s", bank_id, reason)


def parser_failure(logger: logging.Logger, bank_id: str, reason: str) -> None:
    logger.warning("PARSER_FAILURE bank=%s reason=%s", bank_id, reason)


def validation_rejected(logger: logging.Logger, bank_id: str, reason: str) -> None:
    logger.warning("VALIDATION_REJECTED bank=%s reason=%s", bank_id, reason)


def recommendation_generated(logger: logging.Logger, summary: str) -> None:
    logger.info("RECOMMENDATION_GENERATED %s", summary)


def unexpected_value(logger: logging.Logger, bank_id: str, detail: str) -> None:
    logger.warning("UNEXPECTED_VALUE bank=%s detail=%s", bank_id, detail)


def collector_crashed(logger: logging.Logger, bank_id: str, error: Exception) -> None:
    logger.exception("COLLECTOR_CRASHED bank=%s error=%s", bank_id, error)
