import types

from core.collectors import legacy_adapter
from core.config.loader import PlatformConfig
from core.models import Bank, Currency, Product
from core.pipeline import run_collection_cycle
from core.storage import observation_store


def _config_with_banks(*banks: Bank) -> PlatformConfig:
    return PlatformConfig(
        currencies={
            "EUR": Currency(code="EUR", name="Euro", min_rate=120, max_rate=170, max_spread=10),
            "USD": Currency(code="USD", name="US Dollar", min_rate=100, max_rate=150, max_spread=8),
        },
        products={"TT": Product(id="TT", name="Telegraphic Transfer")},
        banks={b.id: b for b in banks},
    )


def _fake_module(get_rates_fn):
    module = types.ModuleType("fake_pipeline_collector")
    module.get_rates = get_rates_fn
    return module


def test_full_cycle_accepts_good_data_and_stores_it(monkeypatch, tmp_path):
    bank = Bank(id="BRAC", name="BRAC Bank PLC", currencies=("EUR", "USD"), products=("TT",),
                collector="fake_pipeline_module", source_type="pdf")
    config = _config_with_banks(bank)

    fake = _fake_module(lambda currencies: [
        {"bank": "BRAC", "currency": "EUR", "buy": 139.0, "sell": 142.0},
        {"bank": "BRAC", "currency": "USD", "buy": 118.0, "sell": 120.5},
    ])
    monkeypatch.setattr(legacy_adapter.importlib, "import_module", lambda name: fake)

    summary = run_collection_cycle(config, storage_dir=tmp_path)

    assert summary.collected == 2
    assert summary.accepted == 2
    assert summary.rejected == 0

    stored = observation_store.load_all("BRAC", storage_dir=tmp_path)
    assert len(stored) == 2


def test_full_cycle_rejects_bad_data_and_does_not_store_it(monkeypatch, tmp_path):
    bank = Bank(id="BRAC", name="BRAC Bank PLC", currencies=("EUR",), products=("TT",),
                collector="fake_pipeline_module", source_type="pdf")
    config = _config_with_banks(bank)

    # 500.0 is nowhere near EUR's [120, 170] range — simulates a parser
    # grabbing the wrong number entirely.
    fake = _fake_module(lambda currencies: [
        {"bank": "BRAC", "currency": "EUR", "buy": 500.0, "sell": 505.0},
    ])
    monkeypatch.setattr(legacy_adapter.importlib, "import_module", lambda name: fake)

    summary = run_collection_cycle(config, storage_dir=tmp_path)

    assert summary.collected == 1
    assert summary.accepted == 0
    assert summary.rejected == 1
    assert summary.rejections[0][0] == "BRAC"

    stored = observation_store.load_all("BRAC", storage_dir=tmp_path)
    assert stored == []  # rejected data must never reach storage


def test_second_cycle_sees_first_cycles_history(monkeypatch, tmp_path):
    """Confirms the pipeline actually uses stored history for the
    historical-validation stage, across separate cycles (like separate
    hourly runs would be)."""
    bank = Bank(id="BRAC", name="BRAC Bank PLC", currencies=("EUR",), products=("TT",),
                collector="fake_pipeline_module", source_type="pdf")
    config = _config_with_banks(bank)

    call_count = {"n": 0}

    def get_rates(currencies):
        call_count["n"] += 1
        # First cycle: a normal rate. Second cycle: a huge, implausible jump.
        buy = 139.0 if call_count["n"] == 1 else 165.0
        return [{"bank": "BRAC", "currency": "EUR", "buy": buy, "sell": buy + 3}]

    fake = _fake_module(get_rates)
    monkeypatch.setattr(legacy_adapter.importlib, "import_module", lambda name: fake)

    first = run_collection_cycle(config, storage_dir=tmp_path)
    second = run_collection_cycle(config, storage_dir=tmp_path)

    assert first.accepted == 1
    assert second.accepted == 0  # rejected as an implausible jump from the first
    assert second.rejected == 1

    # Only the first (good) observation should ever have been stored.
    stored = observation_store.load_all("BRAC", storage_dir=tmp_path)
    assert len(stored) == 1
    assert stored[0].buy == 139.0


def test_one_banks_processing_failure_does_not_stop_the_rest_of_the_cycle(monkeypatch, tmp_path):
    """
    Regression test for a real robustness gap: an unexpected error while
    processing ONE observation (e.g. a storage failure) previously
    crashed the whole loop, silently skipping every other bank in the
    same cycle -- even ones that would have succeeded fine. It must now
    be isolated: the bad one is counted as rejected, everything else
    still gets processed and stored normally.
    """
    good_bank = Bank(id="GOOD", name="Good Bank", currencies=("EUR",), products=("TT",),
                      collector="good_pipeline_module", source_type="pdf")
    bad_bank = Bank(id="BAD", name="Bad Bank", currencies=("EUR",), products=("TT",),
                     collector="bad_pipeline_module", source_type="pdf")
    config = _config_with_banks(good_bank, bad_bank)

    good_module = _fake_module(
        lambda currencies: [{"bank": "GOOD", "currency": "EUR", "buy": 139.0, "sell": 142.0}]
    )
    bad_module = _fake_module(
        lambda currencies: [{"bank": "BAD", "currency": "EUR", "buy": 140.0, "sell": 143.0}]
    )

    def fake_import(name):
        return good_module if name == "good_pipeline_module" else bad_module

    monkeypatch.setattr(legacy_adapter.importlib, "import_module", fake_import)

    # Make storage explode specifically for BAD's observation, simulating
    # something like a disk-write failure.
    real_append = observation_store.append

    def flaky_append(observation, storage_dir=None):
        if observation.bank_id == "BAD":
            raise OSError("simulated disk failure")
        return real_append(observation, storage_dir=storage_dir)

    monkeypatch.setattr(observation_store, "append", flaky_append)

    summary = run_collection_cycle(config, storage_dir=tmp_path)

    assert summary.collected == 2
    assert summary.accepted == 1  # GOOD still succeeded
    assert summary.rejected == 1  # BAD failed, but didn't take GOOD down with it
    assert summary.rejections[0][0] == "BAD"

    stored_good = observation_store.load_all("GOOD", storage_dir=tmp_path)
    assert len(stored_good) == 1
