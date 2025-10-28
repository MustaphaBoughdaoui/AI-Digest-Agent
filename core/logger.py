import logging
import sys
from typing import Optional

from .config import load_app_config


def setup_logging(level_override: Optional[str] = None) -> None:
    config = load_app_config()
    level_name = (level_override or config.get("log_level") or "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
        stream=sys.stdout,
    )
