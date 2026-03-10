"""
fiveg_measure/tests/mtr_test.py — MTR per-hop stability analysis.
Falls back to traceroute-based probing if mtr cannot open raw sockets (common on macOS).
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

# mtr --report-wide output line:
#   1.|-- 10.172.0.1       0.0%     5    1.2   1.4   0.9   2.1   0.3
_MTR_LINE_RE = re.compile(
    r"^\s*(\d+)\.\|[-]+\s+([\d.?*]+)\s+([\d.]+)%\s+\d+\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)"
)

# traceroute -n fallback line (macOS):
#   1  10.172.32.1  59.079 ms  28.932 ms  29.552 ms
_TR_LINE_RE = re.compile(
    r"^\s*(\d+)\s+([\d.]+)\s+([\d.]+)\s+ms"
)


def _run_mtr(host: str, count: int, timeout: float) -> tuple[bool, str]:
    """Try mtr --report-wide. Returns (success, stdout)."""
    result = run_cmd(
        ["mtr", "--report-wide", "-n", "-c", str(count), host],
        timeout=timeout,
    )
    # Check for raw socket failure
    if "Failure to open" in result.stderr or "Failure to start" in result.stderr:
        return False, result.stdout
    return result.ok, result.stdout + result.stderr


def _run_traceroute_fallback(host: str, timeout: float) -> str:
    """Fallback: use traceroute with timing info."""
    result = run_cmd(["traceroute", "-n", "-q", "3", host], timeout=timeout)
    return result.stdout


def run(cfg: Config, outdir: Path, run_id: str, iteration: int) -> list[dict[str, Any]]:
    test_id = str(uuid.uuid4())
    host = cfg.server["host"]
    mtr_cfg = cfg.section("mtr")
    count = int(mtr_cfg.get("count", 20))
    delim = cfg.output.get("csv_delimiter", ",")
    tz = cfg.output.get("timezone", "UTC")
    ts = now_iso(tz)

    log.info("[mtr] host=%s count=%d iter=%d", host, count, iteration)

    rows: list[dict] = []
    long_metrics: list[dict] = []
    used_fallback = False

    # Try mtr first
    mtr_ok, mtr_output = _run_mtr(host, count, count * 1.5 + 60)

    if mtr_ok and mtr_output:
        for line in mtr_output.splitlines():
            m = _MTR_LINE_RE.match(line)
            if m:
                hop = int(m.group(1))
                hop_ip = m.group(2)
                loss_pct = float(m.group(3))
                last_ms = float(m.group(4))
                avg_ms = float(m.group(5))
                best_ms = float(m.group(6))
                wrst_ms = float(m.group(7))
                stdev_ms = float(m.group(8))
                rows.append({
                    "run_id": run_id, "test_id": test_id, "iteration": iteration,
                    "timestamp": ts, "hop": hop, "hop_ip": hop_ip,
                    "loss_pct": loss_pct, "last_ms": last_ms,
                    "avg_ms": avg_ms, "best_ms": best_ms,
                    "wrst_ms": wrst_ms, "stdev_ms": stdev_ms,
                    "source": "mtr",
                })
                long_metrics += [
                    {"metric_name": "mtr_loss_pct", "metric_value": loss_pct, "unit": "%", "notes": f"hop={hop}"},
                    {"metric_name": "mtr_avg_ms", "metric_value": avg_ms, "unit": "ms", "notes": f"hop={hop}"},
                ]

    # Fallback to traceroute if mtr failed or produced no data
    if not rows:
        log.warning("[mtr] mtr unavailable or failed, falling back to traceroute")
        used_fallback = True
        tr_output = _run_traceroute_fallback(host, 60)

        for line in tr_output.splitlines():
            m = _TR_LINE_RE.match(line)
            if m:
                hop = int(m.group(1))
                hop_ip = m.group(2)
                rtt_ms = float(m.group(3))
                # Extract all RTTs from this line
                rtts = [float(x) for x in re.findall(r"([\d.]+)\s+ms", line)]
                avg_ms = sum(rtts) / len(rtts) if rtts else rtt_ms
                best_ms = min(rtts) if rtts else rtt_ms
                wrst_ms = max(rtts) if rtts else rtt_ms

                rows.append({
                    "run_id": run_id, "test_id": test_id, "iteration": iteration,
                    "timestamp": ts, "hop": hop, "hop_ip": hop_ip,
                    "loss_pct": 0.0, "last_ms": rtt_ms,
                    "avg_ms": round(avg_ms, 3), "best_ms": best_ms,
                    "wrst_ms": wrst_ms, "stdev_ms": 0.0,
                    "source": "traceroute",
                })
                long_metrics += [
                    {"metric_name": "mtr_loss_pct", "metric_value": 0.0, "unit": "%", "notes": f"hop={hop}"},
                    {"metric_name": "mtr_avg_ms", "metric_value": round(avg_ms, 3), "unit": "ms", "notes": f"hop={hop}"},
                ]

    # Store raw output
    if cfg.output.get("store_raw_outputs", True):
        raw_dir = outdir / "raw"
        raw_dir.mkdir(parents=True, exist_ok=True)
        (raw_dir / f"mtr_{test_id}.txt").write_text(mtr_output if not used_fallback else tr_output)

    outdir.mkdir(parents=True, exist_ok=True)
    write_rows(outdir / "mtr.csv", rows, delimiter=delim)
    write_long_form(
        outdir / "measurements_long.csv",
        run_id=run_id, test_id=test_id, test_name="mtr",
        iteration=iteration, timestamp=ts,
        metrics=long_metrics, delimiter=delim,
    )
    source = "traceroute (fallback)" if used_fallback else "mtr"
    log.info("[mtr] done — %d hops (source: %s)", len(rows), source)
    return long_metrics
