"""
core/storage/observation_store.py

Append-only historical storage for validated Observations
(CLAUDE.md "Historical Integrity": never overwrite, corrections create
new observations; spec Ch.8: preserve every validated observation
permanently).

Each bank gets its own file under v2_history/, one JSON object per line
(JSONL). Chosen over v1.0's CSV format because an Observation carries
richer, variable-shaped data (confidence, source type, arbitrary
metadata like student rates) than fixed CSV columns hold comfortably —
but the same underlying idea as v1.0's history/*.csv: plain text files,
committed to git, human-inspectable, no database required.

This is a NEW location, deliberately separate from v1.0's history/*.csv.
Nothing here reads or writes v1.0's history files, so the live dashboard
(which reads history/*.csv and exports/latest.json) is completely
unaffected.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from core.logging_setup import get_logger, unexpected_value
from core.models import Confidence, Observation, SourceType

logger = get_logger("storage.observation_store")

DEFAULT_STORAGE_DIR = Path("v2_history")


def _file_for(bank_id: str, storage_dir: Path) -> Path:
    storage_dir.mkdir(parents=True, exist_ok=True)
    return storage_dir / f"{bank_id}.jsonl"


def _to_json_line(observation: Observation) -> str:
    payload = {
        "bank_id": observation.bank_id,
        "currency": observation.currency,
        "product_id": observation.product_id,
        "buy": observation.buy,
        "sell": observation.sell,
        "collected_at": observation.collected_at.isoformat(),
        "source_type": observation.source_type.value,
        "confidence": observation.confidence.value,
        "rate_date": observation.rate_date,
        "is_stale": observation.is_stale,
        "raw_source": observation.raw_source,
        "metadata": observation.metadata,
    }
    return json.dumps(payload, sort_keys=True)


def _from_json_line(line: str) -> Observation:
    data = json.loads(line)
    return Observation(
        bank_id=data["bank_id"],
        currency=data["currency"],
        product_id=data["product_id"],
        buy=data["buy"],
        sell=data["sell"],
        collected_at=datetime.fromisoformat(data["collected_at"]),
        source_type=SourceType(data["source_type"]),
        confidence=Confidence(data["confidence"]),
        rate_date=data.get("rate_date"),
        is_stale=data.get("is_stale", False),
        raw_source=data.get("raw_source"),
        metadata=data.get("metadata", {}),
    )


def append(observation: Observation, storage_dir: Path = DEFAULT_STORAGE_DIR) -> None:
    """
    Permanently add one validated Observation to history.

    Deliberately opens the file in append ("a") mode only — never "w"
    (write/truncate) — so it is structurally impossible for this
    function to overwrite or delete an existing record. That's the
    mechanism behind "historical observations are immutable," not just a
    convention someone has to remember to follow.
    """
    path = _file_for(observation.bank_id, storage_dir)
    with path.open("a", encoding="utf-8") as f:
        f.write(_to_json_line(observation) + "\n")


def load_all(bank_id: str, storage_dir: Path = DEFAULT_STORAGE_DIR) -> list[Observation]:
    """
    Load every stored observation for a bank, oldest first (file order).

    A single malformed line — e.g. from a process being killed mid-write
    during a crash or power loss, leaving a truncated final line — is
    skipped and logged, not allowed to fail the entire load. Without
    this, one bad line would silently take down historical validation
    (and, transitively, the whole collection cycle) for every bank, not
    just the affected one — exactly what CLAUDE.md's "one failure
    should never stop the platform" principle rules out.
    """
    path = _file_for(bank_id, storage_dir)
    if not path.exists():
        return []

    observations = []
    with path.open("r", encoding="utf-8") as f:
        for line_number, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                observations.append(_from_json_line(line))
            except (json.JSONDecodeError, ValueError, KeyError) as e:
                unexpected_value(
                    logger,
                    bank_id,
                    f"skipping corrupted line {line_number} in {path}: {e}",
                )
                continue
    return observations


def load_recent(
    bank_id: str,
    currency: str,
    product_id: str,
    limit: int = 5,
    storage_dir: Path = DEFAULT_STORAGE_DIR,
) -> list[Observation]:
    """
    Load the most recent `limit` observations for one bank/currency/
    product combination, most recent first — the shape
    core.validation.historical.check_against_recent_history expects.
    """
    matching = [
        o
        for o in load_all(bank_id, storage_dir)
        if o.currency == currency and o.product_id == product_id
    ]
    matching.sort(key=lambda o: o.collected_at, reverse=True)
    return matching[:limit]
