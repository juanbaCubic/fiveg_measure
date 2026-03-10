"""
fiveg_measure/tests/http_download_test.py — HTTP download (or SCP fallback) throughput test.
"""
from __future__ import annotations

import logging
import time
import uuid
from pathlib import Path
from typing import Any

from ..config import Config
from ..utils import write_rows, write_long_form, now_iso

log = logging.getLogger(__name__)


def _http_download(url: str, timeout: float) -> dict:
    import requests
    t0 = time.perf_counter()
    status = 0
    error = ""
    size_bytes = 0
    try:
        resp = requests.get(url, stream=True, timeout=timeout)
        status = resp.status_code
        for chunk in resp.iter_content(chunk_size=65536):
            size_bytes += len(chunk)
    except Exception as exc:
        error = str(exc)
    elapsed_ms = (time.perf_counter() - t0) * 1000
    mbps = (size_bytes * 8 / 1e6) / (elapsed_ms / 1000) if elapsed_ms > 0 else 0
    return {
        "bytes": size_bytes, "duration_ms": round(elapsed_ms, 1),
        "throughput_mbps": round(mbps, 3), "http_status": status, "error": error,
    }


def _scp_download(
    remote_path: str, host: str, user: str,
    ssh_key: Path, ssh_port: int, timeout: float, local_dir: Path,
) -> dict:
    import paramiko

    local_dir.mkdir(parents=True, exist_ok=True)
    local_file = local_dir / Path(remote_path).name
    t0 = time.perf_counter()
    error = ""
    size_bytes = 0
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(
            hostname=host, port=ssh_port, username=user,
            key_filename=str(ssh_key), look_for_keys=False, timeout=30,
        )
        with client.open_sftp() as sftp:
            sftp.get(remote_path, str(local_file))
        client.close()
        size_bytes = local_file.stat().st_size
        local_file.unlink(missing_ok=True)  # cleanup
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
    dl_cfg = cfg.section("http_download")
    urls: list[str] = dl_cfg.get("urls", [])
    timeout = float(dl_cfg.get("timeout_s", 120))
    delim = cfg.output.get("csv_delimiter", ",")
    tz = cfg.output.get("timezone", "UTC")

    rows: list[dict] = []
    long_metrics: list[dict] = []

    if not urls:
        log.info("[http_download] no URLs configured, skipping")
        return long_metrics

    for url in urls:
        ts = now_iso(tz)
        log.info("[http_download] GET %s", url)
        metrics = _http_download(url, timeout)
        rows.append({
            "run_id": run_id, "test_id": test_id, "iteration": iteration,
            "timestamp": ts, "direction": "download", "url": url,
            **metrics,
        })
        if metrics["throughput_mbps"]:
            long_metrics.append({
                "metric_name": "throughput_mbps", "metric_value": metrics["throughput_mbps"],
                "unit": "Mbps", "direction": "DL", "notes": f"url={url}",
            })

    outdir.mkdir(parents=True, exist_ok=True)
    write_rows(outdir / "http_transfer.csv", rows, delimiter=delim)
    write_long_form(
        outdir / "measurements_long.csv",
        run_id=run_id, test_id=test_id, test_name="http_download",
        iteration=iteration, timestamp=now_iso(tz),
        metrics=long_metrics, delimiter=delim,
    )
    log.info("[http_download] done — %d URL(s)", len(rows))
    return long_metrics
