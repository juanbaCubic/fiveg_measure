"""
fiveg_measure/tests/tcp_connect_test.py — TCP connection latency to well-known ports.
"""
from __future__ import annotations

import logging
import socket
import time
import uuid
from pathlib import Path
from typing import Any

from ..config import Config
from ..utils import write_rows, write_long_form, now_iso

log = logging.getLogger(__name__)

DEFAULT_PORTS = [22, 80, 443, 5201]


def _connect(host: str, port: int, timeout: float = 5.0) -> tuple[float | None, bool, str]:
    """Return (connect_time_ms, success, error)."""
    t0 = time.perf_counter()
    try:
        with socket.create_connection((host, port), timeout=timeout):
            elapsed = (time.perf_counter() - t0) * 1000
            return round(elapsed, 3), True, ""
    except OSError as exc:
        elapsed = (time.perf_counter() - t0) * 1000
        return round(elapsed, 3), False, str(exc)


def run(cfg: Config, outdir: Path, run_id: str, iteration: int) -> list[dict[str, Any]]:
    test_id = str(uuid.uuid4())
    host = cfg.server["host"]
    ssh_port = cfg.server.get("ssh_port", 22)
    iperf_port = cfg.server.get("iperf_port", 5201)
    delim = cfg.output.get("csv_delimiter", ",")
    tz = cfg.output.get("timezone", "UTC")

    ports = list({22: ssh_port, 5201: iperf_port, 80: 80, 443: 443}.values())
    ports = sorted(set(ports))

    rows: list[dict] = []
    long_metrics: list[dict] = []

    log.info("[tcp_connect] host=%s ports=%s iter=%d", host, ports, iteration)
    for port in ports:
        ts = now_iso(tz)
        ms, success, error = _connect(host, port)
        rows.append({
            "run_id": run_id, "test_id": test_id, "iteration": iteration,
            "timestamp": ts, "host": host, "port": port,
            "connect_time_ms": ms, "success": success, "error": error,
        })
        if success:
            long_metrics.append({
                "metric_name": "connect_time_ms",
                "metric_value": ms,
                "unit": "ms",
                "notes": f"port={port}",
            })

    outdir.mkdir(parents=True, exist_ok=True)
    write_rows(outdir / "tcp_connect.csv", rows, delimiter=delim)
    write_long_form(
        outdir / "measurements_long.csv",
        run_id=run_id, test_id=test_id, test_name="tcp_connect",
        iteration=iteration, timestamp=now_iso(tz),
        metrics=long_metrics, delimiter=delim,
    )
    log.info("[tcp_connect] done — %d ports probed", len(ports))
    return long_metrics
