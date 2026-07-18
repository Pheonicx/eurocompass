import types

from core.collectors import legacy_adapter, registry
from core.config.loader import PlatformConfig
from core.models import Bank, Currency, Product


def _config_with_one_bank(bank: Bank) -> PlatformConfig:
    return PlatformConfig(
        currencies={
            "EUR": Currency(code="EUR", name="Euro"),
            "USD": Currency(code="USD", name="US Dollar"),
        },
        products={"TT": Product(id="TT", name="Telegraphic Transfer")},
        banks={bank.id: bank},
    )


def _fake_module_with_get_rates(get_rates_fn):
    module = types.ModuleType("fake_multi_collector")
    module.get_rates = get_rates_fn
    return module


def test_prefers_get_rates_when_available(monkeypatch):
    bank = Bank(
        id="FAKE",
        name="Fake Bank",
        currencies=("EUR", "USD"),
        products=("TT",),
        collector="fake_multi_collector_module",
        source_type="pdf",
    )
    config = _config_with_one_bank(bank)

    def fake_get_rates(currencies):
        assert currencies == ("EUR", "USD")  # registry should pass the bank's configured currencies
        return [
            {"bank": "FAKE", "currency": "EUR", "buy": 130.0, "sell": 133.0},
            {"bank": "FAKE", "currency": "USD", "buy": 118.0, "sell": 120.5},
        ]

    fake = _fake_module_with_get_rates(fake_get_rates)
    monkeypatch.setattr(legacy_adapter.importlib, "import_module", lambda name: fake)

    observations = registry.collect_one("FAKE", config)

    assert len(observations) == 2
    currencies_seen = {o.currency for o in observations}
    assert currencies_seen == {"EUR", "USD"}


def test_get_rates_partial_result_still_returns_what_succeeded(monkeypatch):
    """If a bank's PDF has EUR but not USD this run, EUR should still come through."""
    bank = Bank(id="FAKE", name="Fake Bank", currencies=("EUR", "USD"), products=("TT",),
                collector="fake_multi_collector_module", source_type="pdf")
    config = _config_with_one_bank(bank)

    fake = _fake_module_with_get_rates(
        lambda currencies: [{"bank": "FAKE", "currency": "EUR", "buy": 130.0, "sell": 133.0}]
    )
    monkeypatch.setattr(legacy_adapter.importlib, "import_module", lambda name: fake)

    observations = registry.collect_one("FAKE", config)

    assert len(observations) == 1
    assert observations[0].currency == "EUR"


def test_get_rates_crash_does_not_propagate(monkeypatch):
    bank = Bank(id="FAKE", name="Fake Bank", currencies=("EUR", "USD"), products=("TT",),
                collector="fake_multi_collector_module", source_type="pdf")
    config = _config_with_one_bank(bank)

    def boom(currencies):
        raise RuntimeError("PDF layout changed")

    fake = _fake_module_with_get_rates(boom)
    monkeypatch.setattr(legacy_adapter.importlib, "import_module", lambda name: fake)

    assert registry.collect_one("FAKE", config) == []


def test_falls_back_to_get_rate_when_get_rates_absent(monkeypatch):
    """A bank whose collector hasn't been upgraded to get_rates() yet should
    keep working exactly as it did in Phase 1 (single-currency)."""
    bank = Bank(id="FAKE", name="Fake Bank", currencies=("EUR",), products=("TT",),
                collector="fake_single_collector_module", source_type="pdf")
    config = _config_with_one_bank(bank)

    module = types.ModuleType("fake_single_collector")
    module.get_rate = lambda: {"bank": "FAKE", "currency": "EUR", "buy": 130.0, "sell": 133.0}
    monkeypatch.setattr(legacy_adapter.importlib, "import_module", lambda name: module)

    observations = registry.collect_one("FAKE", config)

    assert len(observations) == 1
    assert observations[0].currency == "EUR"


def test_real_collectors_all_expose_get_rates():
    """
    Confirms every one of the 5 real v1.0 collector modules now has the
    new get_rates() function, without actually calling it (which would
    require reaching real bank websites this sandbox can't access).
    """
    import importlib as real_importlib

    from core.config.loader import load_config

    config = load_config()
    for bank in config.banks.values():
        module = real_importlib.import_module(bank.collector)
        assert hasattr(module, "get_rates"), f"{bank.collector} is missing get_rates()"
        assert hasattr(module, "get_rate"), f"{bank.collector} lost its original get_rate()"
