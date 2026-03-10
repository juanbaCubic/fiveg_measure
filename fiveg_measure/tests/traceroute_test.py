"""
fiveg_measure/tests/traceroute_test.py — Traceroute hop analysis.
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

# macOS traceroute -n line:
#  1  10.0.0.1  1.234 ms  1.100 ms  1.456 ms
# or:
#  2  * * *
_HOP_RE = re.compile(
    r"^\s*(\d+)\s+([\d.]+|\*)\s+([\d.]+|\*) ms\s+([\d.]+|\*) ms\s+([\d.]+|\*) ms"
)


def _parse_rtt(val: str) -> float | None:
    if val == "*":
        return None
    try:
        return float(val)
    except ValueError:
        return None


def run(cfg: Config, outdir: Path, run_id: str, iteration: int) -> list[dict[str, Any]]:
    test_id = str(uuid.uuid4())
    host = cfg.server["host"]
    delim = cfg.output.get("csv_delimiter", ",")
    tz = cfg.output.get("timezone", "UTC")
    ts = now_iso(tz)

    log.info("[traceroute] host=%s iter=%d", host, iteration)
    cmd = ["traceroute", "-n", "-m", "30", host]
    result = run_cmd(cmd, timeout=120)

    if cfg.output.get("store_raw_outputs", True):
        raw_dir = outdir / "raw"
        raw_dir.mkdir(parents=True, exist_ok=True)
        (raw_dir / f"traceroute_{test_id}.txt").write_text(result.stdout + result.stderr)

    rows: list[dict] = []
    long_metrics: list[dict] = []

    for line in result.stdout.splitlines():
        m = _HOP_RE.match(line)
        if m:
            hop = int(m.group(1))
            hop_ip = m.group(2)
            r1 = _parse_rtt(m.group(3))
            r2 = _parse_rtt(m.group(4))
            r3 = _parse_rtt(m.group(5))
            rows.append({
                "run_id": run_id, "test_id": test_id, "iteration": iteration,
                "timestamp": ts, "hop": hop, "hop_ip": hop_ip,
                "rtt1_ms": r1, "rtt2_ms": r2, "rtt3_ms": r3,
            })
            # average of non-None RTTs for long form
            rtts = [r for r in (r1, r2, r3) if r is not None]
            if rtts:
                long_metrics.append({
                    "metric_name": "hop_avg_rtt_ms",
                    "metric_value": round(sum(rtts) / len(rtts), 3),
                    "unit": "ms",
                    "notes": f"hop={hop} ip={hop_ip}",
                })

    outdir.mkdir(parents=True, exist_ok=True)
    write_rows(outdir / "traceroute.csv", rows, delimiter=delim)
    write_long_form(
        outdir / "measurements_long.csv",
        run_id=run_id, test_id=test_id, test_name="traceroute",
        iteration=iteration, timestamp=ts,
        metrics=long_metrics, delimiter=delim,
    )
    log.info("[traceroute] done — %d hops", len(rows))
    return long_metrics
