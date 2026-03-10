"""
fiveg_measure/tests/ping_test.py — ICMP ping latency/jitter/loss test.
"""
from __future__ import annotations

import logging
import re
import uuid
from pathlib import Path
from typing import Any

from ..config import Config
from ..utils import run_cmd, write_rows, write_long_form, now_iso

log = logging.getLogger(__name__)

# macOS ping output sample line:
# 64 bytes from 1.2.3.4: icmp_seq=0 ttl=54 time=12.345 ms
_LINE_RE = re.compile(
    r"(\d+) bytes from [\d.]+: icmp_seq=(\d+) ttl=(\d+) time=([\d.]+) ms"
)


def run(cfg: Config, outdir: Path, run_id: str, iteration: int) -> list[dict[str, Any]]:
    """Run ping test; return list of long-form metric rows."""
    test_id = str(uuid.uuid4())
    host = cfg.server["host"]
    ping_cfg = cfg.section("ping")
    count = int(ping_cfg.get("count", 30))
    interval = float(ping_cfg.get("interval", 0.2))
    payload = int(ping_cfg.get("payload_bytes", 56))
    delim = cfg.output.get("csv_delimiter", ",")
    tz = cfg.output.get("timezone", "UTC")

    ts_start = now_iso(tz)
    log.info("[ping] host=%s count=%d iter=%d", host, count, iteration)

    cmd = [
        "ping", "-c", str(count),
        "-i", str(interval),
        "-s", str(payload),
        host,
    ]
    result = run_cmd(cmd, timeout=count * interval + 30)

    # Store raw output
    raw_dir = outdir / "raw"
    if cfg.output.get("store_raw_outputs", True):
        raw_dir.mkdir(parents=True, exist_ok=True)
        (raw_dir / f"ping_{test_id}.txt").write_text(result.stdout + result.stderr)

    rows: list[dict] = []
    long_metrics: list[dict] = []
    lost_count = 0
    total_seq = 0

    for line in result.stdout.splitlines():
        m = _LINE_RE.search(line)
        if m:
            bytes_val, seq, ttl, rtt = m.group(1), m.group(2), m.group(3), m.group(4)
            total_seq += 1
            ts = now_iso(tz)
            rows.append({
                "run_id": run_id,
                "test_id": test_id,
                "iteration": iteration,
                "timestamp": ts,
                "seq": int(seq),
                "rtt_ms": float(rtt),
                "ttl": int(ttl),
                "bytes": int(bytes_val),
                "lost": False,
            })
            long_metrics.append({"metric_name": "rtt_ms", "metric_value": float(rtt), "unit": "ms"})

    # Detect lost packets from summary line
    # e.g. "3 packets transmitted, 2 packets received, 33.3% packet loss"
    for line in result.stdout.splitlines():
        pm = re.search(r"(\d+) packets transmitted, (\d+) packets received", line)
        if pm:
            tx, rx = int(pm.group(1)), int(pm.group(2))
            lost_count = tx - rx
            for _ in range(lost_count):
                rows.append({
                    "run_id": run_id, "test_id": test_id, "iteration": iteration,
                    "timestamp": ts_start, "seq": -1, "rtt_ms": None,
                    "ttl": None, "bytes": None, "lost": True,
                })
            break

    # Write per-packet CSV
    outdir.mkdir(parents=True, exist_ok=True)
    write_rows(outdir / "ping.csv", rows, delimiter=delim)

    # Summary
    rtts = [r["rtt_ms"] for r in rows if r["rtt_ms"] is not None]
    if rtts:
        import statistics
        summary = {
            "run_id": run_id, "test_id": test_id, "iteration": iteration,
            "timestamp": ts_start, "host": host,
            "count": count, "lost": lost_count,
            "loss_pct": round(lost_count / count * 100, 2) if count else 0,
            "rtt_min_ms": min(rtts), "rtt_max_ms": max(rtts),
            "rtt_avg_ms": round(statistics.mean(rtts), 3),
            "rtt_p50_ms": round(statistics.median(rtts), 3),
            "rtt_stdev_ms": round(statistics.stdev(rtts), 3) if len(rtts) > 1 else 0,
        }
        write_rows(outdir / "ping_summary.csv", [summary], delimiter=delim)
        long_metrics += [
            {"metric_name": "loss_pct", "metric_value": summary["loss_pct"], "unit": "%"},
            {"metric_name": "rtt_avg_ms", "metric_value": summary["rtt_avg_ms"], "unit": "ms"},
            {"metric_name": "rtt_p50_ms", "metric_value": summary["rtt_p50_ms"], "unit": "ms"},
        ]

    # Write long-form
    write_long_form(
        outdir / "measurements_long.csv",
        run_id=run_id, test_id=test_id, test_name="ping",
        iteration=iteration, timestamp=ts_start,
        metrics=long_metrics, delimiter=delim,
    )

    log.info("[ping] done — %d rows, %d lost", len(rows), lost_count)
    return long_metrics
