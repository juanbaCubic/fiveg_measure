"""
fiveg_measure/tests/metadata_probe.py — Collect run metadata and system info.
"""
from __future__ import annotations

import logging
import threading
import time
import uuid
from pathlib import Path
from typing import Any

import psutil

from ..config import Config
from ..utils import (
    get_interface_info, wifi_active, get_public_ip,
    get_mac_model, macos_version, now_iso, write_rows,
)

log = logging.getLogger(__name__)


def collect_run_metadata(cfg: Config, run_id: str, tag: str, outdir: Path) -> dict:
    """Collect and write run_metadata.csv. Return metadata dict."""
    tz = cfg.output.get("timezone", "UTC")
    iface = cfg.client.get("interface", "en0")
    iface_info = get_interface_info(iface)
    wifi = wifi_active()
    if wifi and not cfg.client.get("disable_wifi_check", False):
        log.warning("Wi-Fi appears active! For 5G Ethernet measurements, consider disabling Wi-Fi.")

    public_ip = ""
    try:
        public_ip = get_public_ip(timeout=5)
    except Exception:
        pass

    meta = {
        "run_id": run_id,
        "tag": tag,
        "timestamp_start": now_iso(tz),
        "timestamp_end": "",  # filled later
        "macos_version": macos_version(),
        "mac_model": get_mac_model(),
        **iface_info,
        "wifi_active": wifi,
        "public_ip": public_ip,
        "server_host": cfg.server.get("host", ""),
        "iperf_port": cfg.server.get("iperf_port", 5201),
        # Router signal fields (populated by router_probe if available)
        "router_tech": "",
        "router_rsrp": "",
        "router_rsrq": "",
        "router_sinr": "",
        "router_band": "",
        "router_cell_id": "",
    }

    # Optional: try router probe
    try:
        from .router_probe import probe
        router_info = probe(cfg)
        meta.update({
            "router_tech": router_info.get("tech", ""),
            "router_rsrp": router_info.get("rsrp", ""),
            "router_rsrq": router_info.get("rsrq", ""),
            "router_sinr": router_info.get("sinr", ""),
            "router_band": router_info.get("band", ""),
            "router_cell_id": router_info.get("cell_id", ""),
        })
    except Exception:
        pass

    outdir.mkdir(parents=True, exist_ok=True)
    write_rows(outdir / "run_metadata.csv", [meta], delimiter=cfg.output.get("csv_delimiter", ","))
    return meta


class SystemMetricsCollector:
    """Background thread that samples CPU/memory/net every second into system_metrics.csv."""

    def __init__(self, cfg: Config, outdir: Path, run_id: str, test_id: str = ""):
        self._cfg = cfg
        self._outdir = outdir
        self._run_id = run_id
        self._test_id = test_id
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=5)

    def _loop(self) -> None:
        outdir = self._outdir
        delim = self._cfg.output.get("csv_delimiter", ",")
        tz = self._cfg.output.get("timezone", "UTC")
        net_start = psutil.net_io_counters()
        rows_buffer: list[dict] = []

        while not self._stop.is_set():
            ts = now_iso(tz)
            cpu = psutil.cpu_percent(interval=None)
            mem = psutil.virtual_memory().used / (1024 * 1024)  # MB
            net = psutil.net_io_counters()
            rows_buffer.append({
                "run_id": self._run_id,
                "test_id": self._test_id,
                "timestamp": ts,
                "cpu_percent": round(cpu, 1),
                "mem_used_mb": round(mem, 1),
                "net_bytes_sent": net.bytes_sent,
                "net_bytes_recv": net.bytes_recv,
            })
            # Flush every 10 rows to avoid memory build-up
            if len(rows_buffer) >= 10:
                write_rows(outdir / "system_metrics.csv", rows_buffer, delimiter=delim)
                rows_buffer.clear()
            time.sleep(1)

        if rows_buffer:
            write_rows(outdir / "system_metrics.csv", rows_buffer,
                       delimiter=self._cfg.output.get("csv_delimiter", ","))
