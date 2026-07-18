from core.models import Confidence, Observation, SourceType, utc_now
from core.storage import observation_store


def _obs(bank_id="BRAC", currency="EUR", buy=139.0, sell=142.0):
    return Observation(
        bank_id=bank_id,
        currency=currency,
        product_id="TT",
        buy=buy,
        sell=sell,
        collected_at=utc_now(),
        source_type=SourceType.PDF,
        confidence=Confidence.MEDIUM,
        metadata={"note": "test"},
    )


def test_append_and_load_roundtrip(tmp_path):
    obs = _obs()
    observation_store.append(obs, storage_dir=tmp_path)

    loaded = observation_store.load_all("BRAC", storage_dir=tmp_path)

    assert len(loaded) == 1
    assert loaded[0].bank_id == "BRAC"
    assert loaded[0].buy == 139.0
    assert loaded[0].sell == 142.0
    assert loaded[0].metadata == {"note": "test"}


def test_multiple_appends_never_overwrite_earlier_ones(tmp_path):
    """This is the core Historical Integrity guarantee, proven, not assumed."""
    observation_store.append(_obs(buy=139.0), storage_dir=tmp_path)
    observation_store.append(_obs(buy=140.0), storage_dir=tmp_path)
    observation_store.append(_obs(buy=141.0), storage_dir=tmp_path)

    loaded = observation_store.load_all("BRAC", storage_dir=tmp_path)

    assert len(loaded) == 3
    assert [o.buy for o in loaded] == [139.0, 140.0, 141.0]


def test_load_all_for_unknown_bank_returns_empty_list(tmp_path):
    assert observation_store.load_all("NOPE", storage_dir=tmp_path) == []


def test_load_recent_filters_by_currency_and_product(tmp_path):
    observation_store.append(_obs(currency="EUR", buy=139.0), storage_dir=tmp_path)
    observation_store.append(_obs(currency="USD", buy=118.0), storage_dir=tmp_path)
    observation_store.append(_obs(currency="EUR", buy=140.0), storage_dir=tmp_path)

    recent_eur = observation_store.load_recent("BRAC", "EUR", "TT", storage_dir=tmp_path)

    assert len(recent_eur) == 2
    assert all(o.currency == "EUR" for o in recent_eur)


def test_load_recent_orders_most_recent_first_and_respects_limit(tmp_path):
    for buy in (100.0, 101.0, 102.0, 103.0):
        observation_store.append(_obs(buy=buy), storage_dir=tmp_path)

    recent = observation_store.load_recent("BRAC", "EUR", "TT", limit=2, storage_dir=tmp_path)

    assert len(recent) == 2
    assert recent[0].buy == 103.0  # most recent first
    assert recent[1].buy == 102.0


def test_different_banks_are_stored_separately(tmp_path):
    observation_store.append(_obs(bank_id="BRAC"), storage_dir=tmp_path)
    observation_store.append(_obs(bank_id="CITY"), storage_dir=tmp_path)

    assert len(observation_store.load_all("BRAC", storage_dir=tmp_path)) == 1
    assert len(observation_store.load_all("CITY", storage_dir=tmp_path)) == 1
