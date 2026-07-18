"""
core/config/loader.py

Loads core/config/banks.json into the typed models defined in
core/models.py.

This is the one place in the codebase that knows the config file's exact
shape. Everything downstream (the collector registry, validation,
recommendations, dashboard, Telegram bot, API) works with Bank/Currency/
Product objects and never reads the JSON file directly. That's what makes
"add a bank" a one-file config change instead of a hunt through the
codebase (CLAUDE.md: "Configuration over Hardcoding", "Plugin Mindset").
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import NamedTuple

from core.models import Bank, Currency, Product

DEFAULT_CONFIG_PATH = Path(__file__).parent / "banks.json"


class PlatformConfig(NamedTuple):
    """Everything loaded from banks.json, as typed objects."""

    currencies: dict[str, Currency]  # keyed by currency code
    products: dict[str, Product]  # keyed by product id
    banks: dict[str, Bank]  # keyed by bank id


class ConfigError(Exception):
    """Raised when core/config/banks.json is missing required fields or is malformed."""


def load_config(path: Path | None = None) -> PlatformConfig:
    """
    Load and validate the platform configuration.

    Raises ConfigError with a clear, specific message if anything is
    missing or inconsistent (e.g. a bank references a currency that isn't
    declared) — per CLAUDE.md's "Never bypass validation" principle,
    misconfiguration should fail loudly here rather than surface as a
    confusing bug somewhere downstream.
    """
    config_path = path or DEFAULT_CONFIG_PATH

    if not config_path.exists():
        raise ConfigError(f"Config file not found: {config_path}")

    try:
        raw = json.loads(config_path.read_text())
    except json.JSONDecodeError as e:
        raise ConfigError(f"Config file is not valid JSON: {config_path} ({e})") from e

    currencies = _load_currencies(raw)
    products = _load_products(raw)
    banks = _load_banks(raw, currencies, products)

    return PlatformConfig(currencies=currencies, products=products, banks=banks)


def _load_currencies(raw: dict) -> dict[str, Currency]:
    currencies: dict[str, Currency] = {}
    for entry in raw.get("currencies", []):
        try:
            kwargs = {"code": entry["code"], "name": entry["name"]}
        except KeyError as e:
            raise ConfigError(f"Currency entry missing required field {e}: {entry}") from e

        for field_name in ("min_rate", "max_rate", "max_spread"):
            if field_name in entry:
                kwargs[field_name] = entry[field_name]

        currency = Currency(**kwargs)
        currencies[currency.code] = currency
    return currencies


def _load_products(raw: dict) -> dict[str, Product]:
    products: dict[str, Product] = {}
    for entry in raw.get("products", []):
        try:
            product = Product(
                id=entry["id"],
                name=entry["name"],
                description=entry.get("description", ""),
            )
        except KeyError as e:
            raise ConfigError(f"Product entry missing required field {e}: {entry}") from e
        products[product.id] = product
    return products


def _load_banks(
    raw: dict, currencies: dict[str, Currency], products: dict[str, Product]
) -> dict[str, Bank]:
    banks: dict[str, Bank] = {}

    for entry in raw.get("banks", []):
        try:
            bank_id = entry["id"]
            bank_currencies = tuple(entry.get("currencies", []))
            bank_products = tuple(entry.get("products", []))

            for code in bank_currencies:
                if code not in currencies:
                    raise ConfigError(
                        f"Bank '{bank_id}' references undeclared currency '{code}'. "
                        f"Add it to the top-level 'currencies' list in banks.json."
                    )
            for product_id in bank_products:
                if product_id not in products:
                    raise ConfigError(
                        f"Bank '{bank_id}' references undeclared product '{product_id}'. "
                        f"Add it to the top-level 'products' list in banks.json."
                    )

            bank = Bank(
                id=bank_id,
                name=entry["name"],
                currencies=bank_currencies,
                products=bank_products,
                collector=entry.get("collector"),
                source_urls=entry.get("source_urls", {}),
                source_type=entry.get("source_type", "other"),
            )
        except KeyError as e:
            raise ConfigError(f"Bank entry missing required field {e}: {entry}") from e

        if bank.id in banks:
            raise ConfigError(f"Duplicate bank id in config: '{bank.id}'")

        banks[bank.id] = bank

    return banks
