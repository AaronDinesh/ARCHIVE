import logging
from pathlib import Path


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
