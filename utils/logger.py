import logging
from pathlib import Path
from datetime import datetime


LOG_DIR = Path("logs")

logger = logging.getLogger("EuroCompass")

_configured = False


def _ensure_configured():
    """
    Lazily create the log directory and configure file logging on first
    use, rather than at import time. Doing this at import time meant
    that simply importing utils.logger would crash on a read-only or
    restricted working directory (a locked-down CI runner, a sandboxed
    test run) before any of this module's functions were ever called --
    the same bug class already found and fixed in core/logging_setup.py
    and utils/exporter.py.
    """
    global _configured

    if _configured:
        return

    try:
        LOG_DIR.mkdir(exist_ok=True)
        log_file = LOG_DIR / f"{datetime.now().strftime('%Y-%m-%d')}.log"

        logging.basicConfig(
            filename=log_file,
            level=logging.INFO,
            format="%(asctime)s | %(levelname)-8s | %(message)s",
            datefmt="%H:%M:%S",
        )
    except OSError as e:
        # Fall back to whatever default logging config already exists
        # (typically console) rather than crash -- file logging is
        # non-essential.
        print(f"WARNING: could not set up file logging: {e}")

    _configured = True


def log_start():
    _ensure_configured()
    logger.info("=" * 60)
    logger.info("EuroCompass started")


def log_success(bank, buy, sell):
    _ensure_configured()
    logger.info(
        "%s collected successfully | BUY=%.4f SELL=%.4f",
        bank,
        buy,
        sell,
    )


def log_failed(bank):
    _ensure_configured()
    logger.warning("%s collector returned no data", bank)


def log_error(bank, error):
    _ensure_configured()
    logger.exception("%s collector crashed: %s", bank, error)


def log_export(filename):
    _ensure_configured()
    logger.info("Exported %s", filename)


def log_finish():
    _ensure_configured()
    logger.info("EuroCompass finished successfully")