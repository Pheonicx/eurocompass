import json
from pathlib import Path

from core.config.loader import PlatformConfig
from core.export import DEFAULT_SCENARIOS, build_export, write_export
from core.models import Bank, Confidence, Currency, Observation, Product, SourceType, utc_now
from core.storage import observation_store


def _config():
    return PlatformConfig(
        currencies={
            "EUR": Currency(code="EUR", name="Euro", min_rate=120, max_rate=170, max_spread=10),
            "USD": Currency(code="USD", name="US Dollar", min_rate=100, max_rate=150, max_spread=8),
        },
        products={"TT": Product(id="TT", name="Telegraphic Transfer")},
        banks={
            "BRAC": Bank(id="BRAC", name="BRAC Bank PLC", currencies=("EUR", "USD"), products=("TT",)),
            "CITY": Bank(id="CITY", name="City Bank PLC", currencies=("EUR", "USD"), products=("TT",)),
        },
    )


def _seed(storage_dir, bank_id, currency, sell):
    obs = Observation(
        bank_id=bank_id,
        currency=currency,
        product_id="TT",
        buy=sell - 3,
        sell=sell,
        collected_at=utc_now(),
        source_type=SourceType.PDF,
        confidence=Confidence.HIGH,
    )
    observation_store.append(obs, storage_dir=storage_dir)


def test_build_export_includes_rates_and_recommendation(tmp_path):
    config = _config()
    _seed(tmp_path, "BRAC", "EUR", 142.0)
    _seed(tmp_path, "CITY", "EUR", 140.0)

    data = build_export(config, storage_dir=tmp_path, scenarios=(("EUR", "TT", 1000.0),))

    assert "EUR" in data["rates_by_currency"]
    assert len(data["rates_by_currency"]["EUR"]) == 2
    # cheapest (lowest sell) should be listed first
    assert data["rates_by_currency"]["EUR"][0]["bank_id"] == "CITY"

    assert len(data["recommendations"]) == 1
    rec = data["recommendations"][0]
    assert rec["recommended_bank_id"] == "CITY"
    assert rec["recommended_bank_name"] == "City Bank PLC"
    assert "CITY" in rec["explanation"] or "City Bank PLC" in rec["explanation"]


def test_scenario_with_no_data_is_skipped_not_errored(tmp_path):
    config = _config()
    # No USD data seeded at all.
    data = build_export(config, storage_dir=tmp_path, scenarios=(("USD", "TT", 500.0),))

    assert data["rates_by_currency"] == {}
    assert data["recommendations"] == []


def test_single_observation_produces_no_trend(tmp_path):
    """One data point can't show a trend — must not be reported as one."""
    config = _config()
    _seed(tmp_path, "BRAC", "EUR", 142.0)

    data = build_export(config, storage_dir=tmp_path, scenarios=(("EUR", "TT", 1000.0),))

    assert data["trends_by_currency"]["EUR"] == []


def test_multiple_observations_produce_a_trend(tmp_path):
    config = _config()
    _seed(tmp_path, "BRAC", "EUR", 140.0)
    _seed(tmp_path, "BRAC", "EUR", 142.0)
    _seed(tmp_path, "BRAC", "EUR", 145.0)

    data = build_export(config, storage_dir=tmp_path, scenarios=(("EUR", "TT", 1000.0),))

    trends = data["trends_by_currency"]["EUR"]
    assert len(trends) == 1
    assert trends[0]["bank_id"] == "BRAC"
    assert trends[0]["direction"] == "rising"
    assert "description" in trends[0]


def test_default_scenarios_cover_eur_and_usd():
    currencies = {s[0] for s in DEFAULT_SCENARIOS}
    assert currencies == {"EUR", "USD"}


def test_write_export_creates_valid_json_file(tmp_path):
    config = _config()
    _seed(tmp_path, "BRAC", "EUR", 142.0)

    export_path = tmp_path / "exports" / "latest.json"
    result_path = write_export(
        config,
        storage_dir=tmp_path,
        export_path=export_path,
        scenarios=(("EUR", "TT", 1000.0),),
    )

    assert result_path == export_path
    assert export_path.exists()

    loaded = json.loads(export_path.read_text())
    assert "generated_at" in loaded
    assert "EUR" in loaded["rates_by_currency"]


def test_write_export_does_not_touch_v1_exports_file(tmp_path):
    """v1.0's exports/latest.json must never be written to by this module."""
    config = _config()
    _seed(tmp_path, "BRAC", "EUR", 142.0)

    v2_path = tmp_path / "v2_exports" / "latest.json"
    write_export(config, storage_dir=tmp_path, export_path=v2_path,
                 scenarios=(("EUR", "TT", 1000.0),))

    v1_path = tmp_path / "exports" / "latest.json"
    assert not v1_path.exists()
