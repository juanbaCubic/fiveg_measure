"""
fiveg_measure/tests/iperf_udp_test.py — iPerf3 UDP jitter/loss under simulated video load.
"""
from __future__ import annotations

import json
import logging
import uuid
from pathlib import Path
from typing import Any

from ..config import Config
from ..utils import run_cmd, write_rows, write_long_form, now_iso

log = logging.getLogger(__name__)


def run(cfg: Config, outdir: Path, run_id: str, iteration: int) -> list[dict[str, Any]]:
    test_id = str(uuid.uuid4())
    host = cfg.server["host"]
    port = cfg.server.get("iperf_port", 5201)
    udp_cfg = cfg.section("iperf_udp")
    duration = int(udp_cfg.get("duration_s", 10))
    bitrates: list[int] = udp_cfg.get("bitrates_mbps_list", [5, 10, 20, 40])
    pkt_len = int(udp_cfg.get("packet_len_bytes", 1400))
    delim = cfg.output.get("csv_delimiter", ",")
    tz = cfg.output.get("timezone", "UTC")
    raw_dir = outdir / "raw"

    summary_rows: list[dict] = []
    long_metrics: list[dict] = []

    for rate_mbps in bitrates:
        ts = now_iso(tz)
        log.info("[iperf_udp] bitrate=%d Mbps iter=%d", rate_mbps, iteration)
        cmd = [
            "iperf3", "-c", host, "-p", str(port),
            "-u", "-b", f"{rate_mbps}M",
            "-t", str(duration),
            "--len", str(pkt_len),
            "--json",
        ]
        result = run_cmd(cmd, timeout=duration + 30)

        if cfg.output.get("store_raw_outputs", True):
            raw_dir.mkdir(parents=True, exist_ok=True)
            (raw_dir / f"iperf_udp_{rate_mbps}mbps_{test_id}.json").write_text(result.stdout)

        data = None
        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError:
            log.warning("[iperf_udp] Could not parse JSON at %d Mbps", rate_mbps)

        if not data or "error" in data:
            err = data.get("error", "unknown") if data else "no JSON"
            summary_rows.append({
                "run_id": run_id, "test_id": test_id, "iteration": iteration,
                "timestamp": ts, "bitrate_mbps": rate_mbps, "duration_s": duration,
                "jitter_ms": None, "lost_packets": None, "total_packets": None,
                "loss_pct": None, "out_of_order": None, "avg_mbps": None, "error": str(err),
            })
            continue

        end = data.get("end", {})
        udp_sum = end.get("sum", {})
        jitter_ms = udp_sum.get("jitter_ms", None)
        lost = udp_sum.get("lost_packets", None)
        total = udp_sum.get("packets", None)
        out_of_order = udp_sum.get("out_of_order", None)
        loss_pct = udp_sum.get("lost_percent", None)
        bps = udp_sum.get("bits_per_second", None)
        avg_mbps = bps / 1e6 if bps else None

        summary_rows.append({
            "run_id": run_id, "test_id": test_id, "iteration": iteration,
            "timestamp": ts, "bitrate_mbps": rate_mbps, "duration_s": duration,
            "jitter_ms": round(jitter_ms, 4) if jitter_ms is not None else None,
            "lost_packets": lost, "total_packets": total,
            "loss_pct": round(loss_pct, 4) if loss_pct is not None else None,
            "out_of_order": out_of_order,
            "avg_mbps": round(avg_mbps, 3) if avg_mbps else None,
            "error": "",
        })

        if jitter_ms is not None:
            long_metrics.append({
                "metric_name": "jitter_ms",
                "metric_value": round(jitter_ms, 4),
                "unit": "ms",
                "direction": "UL",
                "notes": f"bitrate={rate_mbps}Mbps",
            })
        if loss_pct is not None:
            long_metrics.append({
                "metric_name": "loss_pct",
                "metric_value": round(loss_pct, 4),
                "unit": "%",
                "direction": "UL",
                "notes": f"bitrate={rate_mbps}Mbps",
            })

    outdir.mkdir(parents=True, exist_ok=True)
    write_rows(outdir / "iperf_udp_summary.csv", summary_rows, delimiter=delim)
    write_long_form(
        outdir / "measurements_long.csv",
        run_id=run_id, test_id=test_id, test_name="iperf_udp",
        iteration=iteration, timestamp=now_iso(tz),
        metrics=long_metrics, delimiter=delim,
    )
    log.info("[iperf_udp] done — %d bitrate tests", len(summary_rows))
    return long_metrics
