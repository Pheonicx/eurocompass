import json

import pytest

from core.config.loader import ConfigError, load_config


def test_default_config_loads_all_five_banks():
    config = load_config()
    assert set(config.banks) == {"BRAC", "CITY", "EBL", "PRIME", "SONALI"}
    assert "EUR" in config.currencies
    assert "TT" in config.products


def test_default_config_banks_point_at_real_collector_modules():
    config = load_config()
    for bank in config.banks.values():
        assert bank.collector == f"collectors.{bank.id.lower()}"


def test_rejects_bank_with_undeclared_currency(tmp_path):
    bad_config = {
        "currencies": [{"code": "EUR", "name": "Euro"}],
        "products": [{"id": "TT", "name": "Telegraphic Transfer"}],
        "banks": [
            {
                "id": "FAKE",
                "name": "Fake Bank",
                "currencies": ["GBP"],  # not declared above
                "products": ["TT"],
            }
        ],
    }
    path = tmp_path / "bad_banks.json"
    path.write_text(json.dumps(bad_config))

    with pytest.raises(ConfigError, match="undeclared currency"):
        load_config(path)


def test_rejects_malformed_json(tmp_path):
    path = tmp_path / "broken.json"
    path.write_text("{ this is not valid json")

    with pytest.raises(ConfigError, match="not valid JSON"):
        load_config(path)


def test_rejects_missing_file(tmp_path):
    with pytest.raises(ConfigError, match="not found"):
        load_config(tmp_path / "does_not_exist.json")


def test_rejects_duplicate_bank_ids(tmp_path):
    bad_config = {
        "currencies": [{"code": "EUR", "name": "Euro"}],
        "products": [{"id": "TT", "name": "Telegraphic Transfer"}],
        "banks": [
            {"id": "DUP", "name": "First", "currencies": ["EUR"], "products": ["TT"]},
            {"id": "DUP", "name": "Second", "currencies": ["EUR"], "products": ["TT"]},
        ],
    }
    path = tmp_path / "dup_banks.json"
    path.write_text(json.dumps(bad_config))

    with pytest.raises(ConfigError, match="Duplicate bank id"):
        load_config(path)
