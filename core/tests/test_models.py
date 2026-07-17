import dataclasses

import pytest

from core.models import Confidence, Currency, Observation, SourceType, utc_now


def test_currency_normalizes_code_to_uppercase():
    c = Currency(code="eur", name="Euro")
    assert c.code == "EUR"


def test_currency_rejects_invalid_code():
    with pytest.raises(ValueError):
        Currency(code="EURO", name="Euro")  # too long
    with pytest.raises(ValueError):
        Currency(code="12", name="???")  # not letters


def test_observation_is_immutable():
    obs = Observation(
        bank_id="BRAC",
        currency="EUR",
        product_id="TT",
        buy=130.0,
        sell=133.0,
        collected_at=utc_now(),
        source_type=SourceType.PDF,
        confidence=Confidence.MEDIUM,
    )
    with pytest.raises(dataclasses.FrozenInstanceError):
        obs.buy = 999.0  # type: ignore[misc]


def test_observation_rejects_sell_below_buy():
    with pytest.raises(ValueError):
        Observation(
            bank_id="BRAC",
            currency="EUR",
            product_id="TT",
            buy=133.0,
            sell=130.0,  # invalid: sell < buy
            collected_at=utc_now(),
            source_type=SourceType.PDF,
            confidence=Confidence.MEDIUM,
        )


def test_observation_rejects_non_positive_rates():
    with pytest.raises(ValueError):
        Observation(
            bank_id="BRAC",
            currency="EUR",
            product_id="TT",
            buy=-1.0,
            sell=130.0,
            collected_at=utc_now(),
            source_type=SourceType.PDF,
            confidence=Confidence.MEDIUM,
        )


def test_observation_spread():
    obs = Observation(
        bank_id="BRAC",
        currency="EUR",
        product_id="TT",
        buy=130.0,
        sell=133.5,
        collected_at=utc_now(),
        source_type=SourceType.PDF,
        confidence=Confidence.MEDIUM,
    )
    assert obs.spread == 3.5
