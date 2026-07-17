import types

import pytest

from core.collectors import legacy_adapter, registry
from core.config.loader import PlatformConfig
from core.models import Bank, Currency, Product


def _config_with_one_bank(bank: Bank) -> PlatformConfig:
    return PlatformConfig(
        currencies={"EUR": Currency(code="EUR", name="Euro")},
        products={"TT": Product(id="TT", name="Telegraphic Transfer")},
        banks={bank.id: bank},
    )


def _fake_module(get_rate_fn):
    module = types.ModuleType("fake_collector")
    module.get_rate = get_rate_fn
    return module


def test_collect_one_success(monkeypatch):
    bank = Bank(
        id="FAKE",
        name="Fake Bank",
        currencies=("EUR",),
        products=("TT",),
        collector="fake_collector_module",
        source_urls={"EUR": "https://example.test/rates"},
        source_type="pdf",
    )
    config = _config_with_one_bank(bank)

    fake = _fake_module(lambda: {"bank": "FAKE", "currency": "EUR", "buy": 130.0, "sell": 133.0})
    monkeypatch.setattr(legacy_adapter.importlib, "import_module", lambda name: fake)

    observations = registry.collect_one("FAKE", config)

    assert len(observations) == 1
    obs = observations[0]
    assert obs.bank_id == "FAKE"
    assert obs.buy == 130.0
    assert obs.sell == 133.0
    assert obs.raw_source == "https://example.test/rates"


def test_collect_one_handles_none_result(monkeypatch):
    bank = Bank(id="FAKE", name="Fake Bank", currencies=("EUR",), products=("TT",),
                collector="fake_collector_module", source_type="pdf")
    config = _config_with_one_bank(bank)

    fake = _fake_module(lambda: None)
    monkeypatch.setattr(legacy_adapter.importlib, "import_module", lambda name: fake)

    assert registry.collect_one("FAKE", config) == []


def test_collect_one_survives_crashing_collector(monkeypatch):
    """A collector that raises must not raise out of collect() — CLAUDE.md:
    one failed bank should never stop the platform."""
    bank = Bank(id="FAKE", name="Fake Bank", currencies=("EUR",), products=("TT",),
                collector="fake_collector_module", source_type="pdf")
    config = _config_with_one_bank(bank)

    def boom():
        raise RuntimeError("site is down")

    fake = _fake_module(boom)
    monkeypatch.setattr(legacy_adapter.importlib, "import_module", lambda name: fake)

    assert registry.collect_one("FAKE", config) == []


def test_collect_one_unknown_bank_raises_key_error():
    config = PlatformConfig(currencies={}, products={}, banks={})
    with pytest.raises(KeyError):
        registry.collect_one("NOPE", config)


def test_collect_all_continues_after_one_bank_fails(monkeypatch):
    good_bank = Bank(id="GOOD", name="Good Bank", currencies=("EUR",), products=("TT",),
                      collector="good_module", source_type="pdf")
    bad_bank = Bank(id="BAD", name="Bad Bank", currencies=("EUR",), products=("TT",),
                     collector="bad_module", source_type="pdf")

    config = PlatformConfig(
        currencies={"EUR": Currency(code="EUR", name="Euro")},
        products={"TT": Product(id="TT", name="Telegraphic Transfer")},
        banks={"GOOD": good_bank, "BAD": bad_bank},
    )

    good_module = _fake_module(
        lambda: {"bank": "GOOD", "currency": "EUR", "buy": 130.0, "sell": 133.0}
    )

    def fake_import(name):
        if name == "good_module":
            return good_module
        raise ImportError("no such module")

    monkeypatch.setattr(legacy_adapter.importlib, "import_module", fake_import)

    observations = registry.collect_all(config)

    assert len(observations) == 1
    assert observations[0].bank_id == "GOOD"
