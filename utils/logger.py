import logging
from pathlib import Path
from datetime import datetime


LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

LOG_FILE = LOG_DIR / f"{datetime.now().strftime('%Y-%m-%d')}.log"


logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)


logger = logging.getLogger("EuroCompass")


def log_start():
    logger.info("=" * 60)
    logger.info("EuroCompass started")


def log_success(bank, buy, sell):
    logger.info(
        "%s collected successfully | BUY=%.4f SELL=%.4f",
        bank,
        buy,
        sell,
    )


def log_failed(bank):
    logger.warning("%s collector returned no data", bank)


def log_error(bank, error):
    logger.exception("%s collector crashed: %s", bank, error)


def log_export(filename):
    logger.info("Exported %s", filename)


def log_finish():
    logger.info("EuroCompass finished successfully")