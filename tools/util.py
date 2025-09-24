# tools/util.py
import datetime
import logging
import os
import re
from pathlib import Path

from dotenv import load_dotenv
from unidecode import unidecode

# Load environment variables from .env
load_dotenv()


def slugify(text: str, maxlen: int = 80) -> str:
    """
    Turn any string into a filesystem-safe slug.
    Example: "Logitech International S.A. — Invoice #12345"
    -> "logitech_international_s_a_invoice_12345"
    """
    if not text:
        return ""
    text = unidecode(text)  # remove accents, normalise
    text = re.sub(r"[^\w\s.-]", "", text).strip().lower()  # keep letters, numbers, _, ., -
    text = re.sub(r"[\s]+", "_", text)  # spaces -> underscores
    return text[:maxlen].strip("_")


def today(fmt_env_var="DATE_FMT") -> str:
    """
    Return today’s date formatted according to DATE_FMT in .env,
    or default to YYYY-MM-DD.
    """
    fmt = os.getenv(fmt_env_var, "%Y-%m-%d")
    return datetime.date.today().strftime(fmt)


def _create_log_path(path: Path):
    if not path.exists():
        path.mkdir(parents=True, exist_ok=True)


def get_logger(name: str):
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # create file handler which logs even debug messages
    fname = Path("logs") / f"{name}.log"
    _create_log_path(fname.parent)
    fh = logging.FileHandler(filename=fname)
    fh.setLevel(logging.DEBUG)

    # create formatter and add it to the handlers
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    fh.setFormatter(formatter)

    # add the handlers to the logger
    logger.addHandler(fh)
    return logger
