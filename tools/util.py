# tools/util.py
import os
import re
import datetime
from unidecode import unidecode
from dotenv import load_dotenv

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
