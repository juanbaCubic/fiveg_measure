"""
fiveg_measure/utils/csv_writer.py — Thread-safe CSV append helper.
"""
from __future__ import annotations

import csv
import threading
from pathlib import Path
from typing import Any

_lock = threading.Lock()


def write_rows(path: Path, rows: list[dict[str, Any]], delimiter: str = ",") -> None:
    """Append *rows* to a CSV at *path*, writing header on first write."""
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    write_header = not path.exists() or path.stat().st_size == 0
    fieldnames = list(rows[0].keys())
    with _lock:
        with path.open("a", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=fieldnames, delimiter=delimiter, extrasaction="ignore")
            if write_header:
                writer.writeheader()
            writer.writerows(rows)


def write_long_form(
    path: Path,
    run_id: str,
    test_id: str,
    test_name: str,
    iteration: int,
    timestamp: str,
    metrics: list[dict[str, Any]],
    delimiter: str = ",",
) -> None:
    """Write rows in long-form format to *path*."""
    rows = []
    for m in metrics:
        rows.append(
            {
                "run_id": run_id,
                "test_id": test_id,
                "test_name": test_name,
                "iteration": iteration,
                "timestamp": timestamp,
                "metric_name": m.get("metric_name", ""),
                "metric_value": m.get("metric_value", ""),
                "unit": m.get("unit", ""),
                "direction": m.get("direction", "NA"),
                "notes": m.get("notes", ""),
            }
        )
    write_rows(path, rows, delimiter=delimiter)
