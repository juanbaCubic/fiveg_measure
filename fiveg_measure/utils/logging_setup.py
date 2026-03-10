"""
fiveg_measure/utils/logging_setup.py — Centralised logging configuration.
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path


def setup_logging(level: str = "INFO", logfile: Path | None = None) -> None:
    """Configure root logger for CLI usage."""
    fmt = "%(asctime)s [%(levelname)s] %(name)s — %(message)s"
    datefmt = "%Y-%m-%dT%H:%M:%S"
    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stderr)]
    if logfile:
        logfile.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(logfile, encoding="utf-8"))
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format=fmt,
        datefmt=datefmt,
        handlers=handlers,
        force=True,
    )
