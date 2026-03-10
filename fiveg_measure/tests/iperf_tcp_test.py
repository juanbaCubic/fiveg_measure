"""
fiveg_measure/tests/iperf_tcp_test.py — iPerf3 TCP throughput (UL + DL, single + parallel streams).
"""
from __future__ import annotations

import json
import logging
import statistics
import uuid
from pathlib import Path
from typing import Any

from ..config import Config
from ..utils import run_cmd, write_rows, write_long_form, now_iso

log = logging.getLogger(__name__)


def _parse_iperf_json(raw: str) -> dict | None:
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def _run_one(host: str, port: int, duration: int, streams: int, reverse: bool, extra_timeout: float = 30.0) -> tuple[str, dict | None]:
    """Run iperf3, return (raw_json_str, parsed_data)."""
    cmd = [
        "iperf3", "-c", host, "-p", str(port),
        "-t", str(duration),
        "-P", str(streams),
        "--json",
    ]
    if reverse:
        cmd.append("-R")
    result = run_cmd(cmd, timeout=duration + extra_timeout)
    data = _parse_iperf_json(result.stdout)
    return result.stdout, data


def run(cfg: Config, outdir: Path, run_id: str, iteration: int) -> list[dict[str, Any]]:
    test_id = str(uuid.uuid4())
    host = cfg.server["host"]
    port = cfg.server.get("iperf_port", 5201)
    tcp_cfg = cfg.section("iperf_tcp")
    duration = int(tcp_cfg.get("duration_s", 15))
    streams_list: list[int] = tcp_cfg.get("parallel_streams_list", [1, 4])
    do_reverse: bool = tcp_cfg.get("reverse", True)
    delim = cfg.output.get("csv_delimiter", ",")
    tz = cfg.output.get("timezone", "UTC")
    raw_dir = outdir / "raw"

    interval_rows: list[dict] = []
    summary_rows: list[dict] = []
    long_metrics: list[dict] = []

    directions = [("UL", False)]
    if do_reverse:
        directions.append(("DL", True))

    for direction, rev in directions:
        for streams in streams_list:
            ts = now_iso(tz)
            log.info("[iperf_tcp] dir=%s streams=%d iter=%d", direction, streams, iteration)
            raw, data = _run_one(host, port, duration, streams, rev)

            if cfg.output.get("store_raw_outputs", True):
                raw_dir.mkdir(parents=True, exist_ok=True)
                fname = f"iperf_tcp_{direction.lower()}_s{streams}_{test_id}.json"
                (raw_dir / fname).write_text(raw)

            if not data or "error" in data:
                err = data.get("error", "unknown") if data else "no JSON"
                log.warning("[iperf_tcp] iperf3 error: %s", err)
                summary_rows.append({
                    "run_id": run_id, "test_id": test_id, "iteration": iteration,
                    "timestamp": ts, "direction": direction, "streams": streams,
                    "duration_s": duration, "avg_mbps": None,
                    "p90_mbps": None, "retransmits_total": None, "error": str(err),
                })
                continue

            # Intervals
            mbps_values: list[float] = []
            retransmits_total = 0
            for interval in data.get("intervals", []):
                # sum across stream sockets
                bits = sum(s["bits_per_second"] for s in interval.get("streams", []))
                mbps = bits / 1e6
                mbps_values.append(mbps)
                retransmits = sum(s.get("retransmits", 0) for s in interval.get("streams", []))
                retransmits_total += retransmits
                # RTT from first stream if available
                rtt_ms = None
                if interval.get("streams"):
                    rtt_us = interval["streams"][0].get("rtt", None)
                    if rtt_us is not None:
                        rtt_ms = round(rtt_us / 1000, 3)
                t_start = interval["sum"].get("start", None)
                t_end = interval["sum"].get("end", None)
                interval_rows.append({
                    "run_id": run_id, "test_id": test_id, "iteration": iteration,
                    "timestamp": ts, "direction": direction, "streams": streams,
                    "interval_start_s": t_start, "interval_end_s": t_end,
                    "bps": bits, "mbps": round(mbps, 3),
                    "retransmits": retransmits, "rtt_ms": rtt_ms,
                })

            # Summary
            avg_mbps = statistics.mean(mbps_values) if mbps_values else None
            p90_mbps = None
            if mbps_values:
                sorted_vals = sorted(mbps_values)
                idx = int(len(sorted_vals) * 0.9)
                p90_mbps = sorted_vals[min(idx, len(sorted_vals) - 1)]
            end_sum = data.get("end", {})
            # sum_received has the received side bps; sum_sent has sender side
            if direction == "DL":
                bps_summary = end_sum.get("sum_received", {}).get("bits_per_second", None)
            else:
                bps_summary = end_sum.get("sum_sent", {}).get("bits_per_second", None)
            summary_mbps = bps_summary / 1e6 if bps_summary else avg_mbps

            summary_rows.append({
                "run_id": run_id, "test_id": test_id, "iteration": iteration,
                "timestamp": ts, "direction": direction, "streams": streams,
                "duration_s": duration,
                "avg_mbps": round(summary_mbps, 3) if summary_mbps else None,
                "p90_mbps": round(p90_mbps, 3) if p90_mbps else None,
                "retransmits_total": retransmits_total,
                "error": "",
            })

            if summary_mbps:
                long_metrics.append({
                    "metric_name": "throughput_mbps",
                    "metric_value": round(summary_mbps, 3),
                    "unit": "Mbps",
                    "direction": direction,
                    "notes": f"streams={streams}",
                })

    outdir.mkdir(parents=True, exist_ok=True)
    write_rows(outdir / "iperf_tcp_intervals.csv", interval_rows, delimiter=delim)
    write_rows(outdir / "iperf_tcp_summary.csv", summary_rows, delimiter=delim)
    write_long_form(
        outdir / "measurements_long.csv",
        run_id=run_id, test_id=test_id, test_name="iperf_tcp",
        iteration=iteration, timestamp=now_iso(tz),
        metrics=long_metrics, delimiter=delim,
    )
    log.info("[iperf_tcp] done — %d direction/stream combos", len(summary_rows))
    return long_metrics
