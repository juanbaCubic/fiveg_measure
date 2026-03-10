"""
fiveg_measure/tests/http_upload_test.py — HTTP upload (or SCP fallback) throughput test.
"""
from __future__ import annotations

import logging
import os
import time
import uuid
from pathlib import Path
from typing import Any

from ..config import Config
from ..utils import write_rows, write_long_form, now_iso

log = logging.getLogger(__name__)


def _http_upload(url: str, filepath: Path, timeout: float) -> dict:
    """Upload a file via HTTP PUT/POST and return metrics."""
    import requests
    size_bytes = filepath.stat().st_size
    t0 = time.perf_counter()
    status = 0
    error = ""
    try:
        with filepath.open("rb") as fh:
            resp = requests.put(url, data=fh, timeout=timeout)
        status = resp.status_code
    except Exception as exc:
        error = str(exc)
    elapsed_ms = (time.perf_counter() - t0) * 1000
    mbps = (size_bytes * 8 / 1e6) / (elapsed_ms / 1000) if elapsed_ms > 0 else 0
    return {
        "bytes": size_bytes, "duration_ms": round(elapsed_ms, 1),
        "throughput_mbps": round(mbps, 3), "http_status": status, "error": error,
    }


def _scp_upload(
    filepath: Path, host: str, user: str, remote_path: str,
    ssh_key: Path, ssh_port: int, timeout: float,
) -> dict:
    """Upload via SCP (paramiko) and return metrics."""
    import paramiko

    size_bytes = filepath.stat().st_size
    t0 = time.perf_counter()
    error = ""
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(
            hostname=host, port=ssh_port, username=user,
            key_filename=str(ssh_key), look_for_keys=False, timeout=30,
        )
        with client.open_sftp() as sftp:
            remote_file = f"{remote_path}/{filepath.name}"
            sftp.put(str(filepath), remote_file)
        client.close()
    except Exception as exc:
        error = str(exc)
    elapsed_ms = (time.perf_counter() - t0) * 1000
    mbps = (size_bytes * 8 / 1e6) / (elapsed_ms / 1000) if elapsed_ms > 0 else 0
    return {
        "bytes": size_bytes, "duration_ms": round(elapsed_ms, 1),
        "throughput_mbps": round(mbps, 3), "http_status": 0, "error": error,
    }


def run(cfg: Config, outdir: Path, run_id: str, iteration: int) -> list[dict[str, Any]]:
    test_id = str(uuid.uuid4())
    http_cfg = cfg.section("http_upload")
    files: list[str] = http_cfg.get("files", [])
    timeout = float(http_cfg.get("timeout_s", 120))
    base_url = cfg.server.get("http_base_url", "")
    delim = cfg.output.get("csv_delimiter", ",")
    tz = cfg.output.get("timezone", "UTC")

    rows: list[dict] = []
    long_metrics: list[dict] = []

    if not files:
        log.info("[http_upload] no files configured, skipping")
        return long_metrics

    for filepath_str in files:
        filepath = Path(os.path.expanduser(filepath_str))
        ts = now_iso(tz)
        if not filepath.exists():
            log.warning("[http_upload] file not found: %s", filepath)
            rows.append({
                "run_id": run_id, "test_id": test_id, "iteration": iteration,
                "timestamp": ts, "direction": "upload", "url": str(filepath),
                "bytes": None, "duration_ms": None, "throughput_mbps": None,
                "http_status": None, "error": f"file not found: {filepath}",
            })
            continue

        if base_url:
            url = f"{base_url.rstrip('/')}/upload"
            log.info("[http_upload] HTTP PUT %s -> %s", filepath.name, url)
            metrics = _http_upload(url, filepath, timeout)
        else:
            # SCP fallback
            log.info("[http_upload] SCP fallback for %s", filepath.name)
            metrics = _scp_upload(
                filepath,
                host=cfg.server["host"],
                user=cfg.server.get("ssh_user", "ubuntu"),
                remote_path="/tmp",
                ssh_key=cfg.ssh_key_path,
                ssh_port=cfg.server.get("ssh_port", 22),
                timeout=timeout,
            )
            url = f"scp://{cfg.server['host']}/tmp/{filepath.name}"

        row = {
            "run_id": run_id, "test_id": test_id, "iteration": iteration,
            "timestamp": ts, "direction": "upload", "url": url if base_url else f"scp:{filepath.name}",
            **metrics,
        }
        rows.append(row)
        if metrics["throughput_mbps"]:
            long_metrics.append({
                "metric_name": "throughput_mbps", "metric_value": metrics["throughput_mbps"],
                "unit": "Mbps", "direction": "UL",
                "notes": f"file={filepath.name}",
            })

    outdir.mkdir(parents=True, exist_ok=True)
    write_rows(outdir / "http_transfer.csv", rows, delimiter=delim)
    write_long_form(
        outdir / "measurements_long.csv",
        run_id=run_id, test_id=test_id, test_name="http_upload",
        iteration=iteration, timestamp=now_iso(tz),
        metrics=long_metrics, delimiter=delim,
    )
    log.info("[http_upload] done — %d file(s)", len(rows))
    return long_metrics
