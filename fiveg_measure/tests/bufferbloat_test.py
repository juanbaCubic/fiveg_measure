"""
fiveg_measure/tests/bufferbloat_test.py — Latency under load (bufferbloat) test.

Runs a saturating TCP transfer in parallel with continuous ping to measure RTT increase.
"""
from __future__ import annotations

import logging
import re
import statistics
import subprocess
import threading
import time
import uuid
from pathlib import Path
from typing import Any

from ..config import Config
from ..utils import write_rows, write_long_form, now_iso

log = logging.getLogger(__name__)

_PING_RE = re.compile(r"icmp_seq=(\d+) ttl=\d+ time=([\d.]+) ms")


def _ping_loop(host: str, results: list, stop_event: threading.Event, tz: str) -> None:
    """Run ping in a loop, appending (timestamp, rtt_ms) to results until stop_event."""
    proc = subprocess.Popen(
        ["ping", "-i", "0.2", host],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    try:
        for line in proc.stdout:  # type: ignore[union-attr]
            if stop_event.is_set():
                break
            m = _PING_RE.search(line)
            if m:
                results.append((now_iso(tz), float(m.group(2))))
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()


def run(cfg: Config, outdir: Path, run_id: str, iteration: int) -> list[dict[str, Any]]:
    test_id = str(uuid.uuid4())
    host = cfg.server["host"]
    port = cfg.server.get("iperf_port", 5201)
    bb_cfg = cfg.section("bufferbloat")
    load_dir = bb_cfg.get("load_direction", "downlink")
    idle_count = int(bb_cfg.get("idle_ping_count", 20))
    load_count = int(bb_cfg.get("ping_count", 40))
    delim = cfg.output.get("csv_delimiter", ",")
    tz = cfg.output.get("timezone", "UTC")

    ts_start = now_iso(tz)
    log.info("[bufferbloat] iter=%d load_dir=%s", iteration, load_dir)

    rows: list[dict] = []

    # ── Phase 1: idle ping ────────────────────────────────────────────────────
    log.info("[bufferbloat] idle phase (%d pings)", idle_count)
    idle_results: list[tuple[str, float]] = []
    stop_ev = threading.Event()
    t = threading.Thread(target=_ping_loop, args=(host, idle_results, stop_ev, tz), daemon=True)
    t.start()
    # collect ~idle_count pings at 0.2s interval
    time.sleep(idle_count * 0.2 + 2)
    stop_ev.set()
    t.join(timeout=5)

    for ts, rtt in idle_results:
        rows.append({
            "run_id": run_id, "test_id": test_id, "iteration": iteration,
            "timestamp": ts, "phase": "idle", "rtt_ms": rtt,
        })

    # ── Phase 2: under-load ping ──────────────────────────────────────────────
    log.info("[bufferbloat] load phase — starting iperf (%s)", load_dir)
    is_reverse = (load_dir.lower() == "downlink")
    iperf_cmd = [
        "iperf3", "-c", host, "-p", str(port),
        "-t", str(int(load_count * 0.2 + 10)),
        "-P", "4",
    ]
    if is_reverse:
        iperf_cmd.append("-R")

    iperf_proc = subprocess.Popen(
        iperf_cmd,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    # give iperf a moment to ramp up
    time.sleep(1)

    load_results: list[tuple[str, float]] = []
    stop_ev2 = threading.Event()
    t2 = threading.Thread(target=_ping_loop, args=(host, load_results, stop_ev2, tz), daemon=True)
    t2.start()
    time.sleep(load_count * 0.2 + 2)
    stop_ev2.set()
    t2.join(timeout=5)

    # Terminate iperf
    iperf_proc.terminate()
    try:
        iperf_proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        iperf_proc.kill()

    for ts, rtt in load_results:
        rows.append({
            "run_id": run_id, "test_id": test_id, "iteration": iteration,
            "timestamp": ts, "phase": "load", "rtt_ms": rtt,
        })

    # ── Write CSVs ────────────────────────────────────────────────────────────
    outdir.mkdir(parents=True, exist_ok=True)
    write_rows(outdir / "bufferbloat.csv", rows, delimiter=delim)

    idle_rtts = [r["rtt_ms"] for r in rows if r["phase"] == "idle"]
    load_rtts = [r["rtt_ms"] for r in rows if r["phase"] == "load"]

    def pct(data: list[float], p: float) -> float | None:
        if not data:
            return None
        s = sorted(data)
        idx = int(len(s) * p / 100)
        return s[min(idx, len(s) - 1)]

    summary = {
        "run_id": run_id, "test_id": test_id, "iteration": iteration,
        "timestamp": ts_start,
        "rtt_idle_p50": pct(idle_rtts, 50), "rtt_idle_avg": round(statistics.mean(idle_rtts), 3) if idle_rtts else None,
        "rtt_load_p50": pct(load_rtts, 50), "rtt_load_avg": round(statistics.mean(load_rtts), 3) if load_rtts else None,
        "rtt_load_p95": pct(load_rtts, 95),
        "rtt_increase_ms": round((pct(load_rtts, 50) or 0) - (pct(idle_rtts, 50) or 0), 3),
        "idle_samples": len(idle_rtts), "load_samples": len(load_rtts),
    }
    write_rows(outdir / "bufferbloat_summary.csv", [summary], delimiter=delim)

    long_metrics = []
    for k in ("rtt_idle_p50", "rtt_load_p50", "rtt_increase_ms", "rtt_load_p95"):
        if summary[k] is not None:
            long_metrics.append({"metric_name": k, "metric_value": summary[k], "unit": "ms"})

    write_long_form(
        outdir / "measurements_long.csv",
        run_id=run_id, test_id=test_id, test_name="bufferbloat",
        iteration=iteration, timestamp=ts_start,
        metrics=long_metrics, delimiter=delim,
    )
    log.info("[bufferbloat] done — idle_p50=%.1f ms load_p50=%.1f ms",
             summary["rtt_idle_p50"] or 0, summary["rtt_load_p50"] or 0)
    return long_metrics
