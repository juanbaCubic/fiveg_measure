"""
fiveg_measure/config.py — Configuration loader and validator.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


# ──────────────────────────────────────────────────────────────────────────────
# Default values (mirrors example_config.yaml)
# ──────────────────────────────────────────────────────────────────────────────
# SMART Goals for R3: 
# Latency <= 50ms, PER <= 1%, Throughput HD Video
# ──────────────────────────────────────────────────────────────────────────────

_DEFAULTS: dict[str, Any] = {
    "kpi_targets": {
        "max_latency_p95_ms": 50.0,
        "max_per_udp_pct": 1.0,
        "min_throughput_tcp_mbps": 15.0,
        "max_mec_latency_ms": 500.0,
        "min_uptime_pct": 99.0,
    },
    "server": {
        "host": "",
        "ssh_user": "ubuntu",
        "ssh_key_path": "~/.ssh/id_rsa",
        "ssh_port": 22,
        "ssh_password": "",
        "iperf_port": 5201,
        "http_base_url": "",
        "video_endpoint": "",
    },
    "client": {
        "interface": "en0",
        "disable_wifi_check": False,
        "time_sync_check": True,
    },
    "suite": {
        "iterations": 3,
        "warmup_seconds": 2,
        "cooldown_seconds": 3,
    },
    "ping": {
        "count": 30,
        "interval": 0.2,
        "payload_bytes": 56,
    },
    "mtr": {
        "count": 20,
    },
    "feko_correlation": {
        "expected_rsrp": -90,
        "expected_sinr": 15,
        "site_id": "",
    },
    "iperf_tcp": {
        "duration_s": 15,
        "parallel_streams_list": [1, 4],
        "reverse": True,
    },
    "iperf_udp": {
        "duration_s": 10,
        "bitrates_mbps_list": [5, 10, 20, 40],
        "packet_len_bytes": 1400,
    },
    "bufferbloat": {
        "load_direction": "downlink",
        "ping_count": 40,
        "idle_ping_count": 20,
    },
    "http_upload": {
        "files": [],
        "timeout_s": 120,
    },
    "http_download": {
        "urls": [],
        "timeout_s": 120,
    },
    "output": {
        "csv_delimiter": ",",
        "timezone": "UTC",
        "store_raw_outputs": True,
    },
}


def _deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge *override* into *base*."""
    result = dict(base)
    for key, val in override.items():
        if isinstance(val, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], val)
        else:
            result[key] = val
    return result


@dataclass
class Config:
    """Flat-ish wrapper around the merged YAML config dict."""

    raw: dict[str, Any]

    # ── convenience properties ────────────────────────────────────────────────

    @property
    def server(self) -> dict:
        return self.raw["server"]

    @property
    def client(self) -> dict:
        return self.raw["client"]

    @property
    def suite(self) -> dict:
        return self.raw["suite"]

    @property
    def output(self) -> dict:
        return self.raw["output"]

    def section(self, name: str) -> dict:
        return self.raw.get(name, {})

    # ── path helpers ──────────────────────────────────────────────────────────

    @property
    def ssh_key_path(self) -> Path | None:
        path_str = self.server.get("ssh_key_path")
        if not path_str:
            return None
        return Path(os.path.expanduser(path_str))

    @property
    def ssh_password(self) -> str | None:
        return self.server.get("ssh_password")

    # ── validation ────────────────────────────────────────────────────────────

    def validate(self) -> list[str]:
        """Return list of validation error strings (empty = OK)."""
        errors: list[str] = []
        if not self.server.get("host"):
            errors.append("server.host is required")
        
        # Check for either key or password
        if not self.server.get("ssh_key_path") and not self.server.get("ssh_password"):
            errors.append("Either server.ssh_key_path or server.ssh_password must be provided")
        
        return errors


def load_config(path: str | Path) -> Config:
    """Load and validate a YAML config file."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    with path.open() as fh:
        user_data = yaml.safe_load(fh) or {}
    merged = _deep_merge(_DEFAULTS, user_data)
    cfg = Config(raw=merged)
    errors = cfg.validate()
    if errors:
        raise ValueError("Config validation errors:\n" + "\n".join(f"  • {e}" for e in errors))
    return cfg
