"""
fiveg_measure/dashboard/server.py — Lightweight HTTP server for the dashboard.

Serves static files from ./static/ and a JSON REST API backed by CSV files.

API endpoints:
  GET /api/runs            → list of run_ids + tags from run_metadata.csv
  GET /api/metrics?run_id= → all metrics from measurements_long.csv for a run
  GET /api/system?run_id=  → system_metrics.csv rows for a run
  GET /api/metadata?run_id=→ single run metadata row
  GET /api/location        → IP-based geolocation (public IP from run_metadata)
"""
from __future__ import annotations

import csv
import io
import json
import logging
import os
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# CSV helpers
# ──────────────────────────────────────────────────────────────────────────────

def _read_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _find_csvs(indir: Path, filename: str) -> list[Path]:
    return sorted(indir.rglob(filename))


# ──────────────────────────────────────────────────────────────────────────────
# Request handler
# ──────────────────────────────────────────────────────────────────────────────

class DashboardHandler(BaseHTTPRequestHandler):
    # Injected by start_server()
    indir: Path = Path("results")
    static_dir: Path = Path(__file__).parent / "static"

    def log_message(self, fmt, *args):  # suppress default access log
        log.debug("HTTP %s", fmt % args)

    def _json(self, data: Any, status: int = 200) -> None:
        body = json.dumps(data, ensure_ascii=False, default=str).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _static(self, path: str) -> None:
        if path == "/" or path == "":
            path = "/index.html"
        fpath = self.static_dir / path.lstrip("/")
        if not fpath.exists() or not fpath.is_file():
            self.send_error(404, f"Not found: {path}")
            return
        mime = {
            ".html": "text/html; charset=utf-8",
            ".css": "text/css",
            ".js": "application/javascript",
            ".json": "application/json",
        }.get(fpath.suffix, "application/octet-stream")
        body = fpath.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):  # noqa: N802
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        params = dict(urllib.parse.parse_qsl(parsed.query))

        if path.startswith("/api/"):
            self._handle_api(path, params)
        else:
            self._static(path)

    def _handle_api(self, path: str, params: dict) -> None:
        try:
            if path == "/api/runs":
                self._api_runs()
            elif path == "/api/metrics":
                self._api_metrics(params.get("run_id", ""))
            elif path == "/api/system":
                self._api_system(params.get("run_id", ""))
            elif path == "/api/metadata":
                self._api_metadata(params.get("run_id", ""))
            elif path == "/api/location":
                self._api_location(params.get("run_id", ""))
            else:
                self._json({"error": "Unknown endpoint"}, 404)
        except Exception as exc:
            log.exception("API error: %s", exc)
            self._json({"error": str(exc)}, 500)

    def _api_runs(self) -> None:
        runs: list[dict] = []
        seen: set[str] = set()
        for fpath in _find_csvs(self.indir, "run_metadata.csv"):
            for row in _read_csv(fpath):
                rid = row.get("run_id", "")
                if rid and rid not in seen:
                    seen.add(rid)
                    runs.append({
                        "run_id": rid,
                        "tag": row.get("tag", ""),
                        "timestamp_start": row.get("timestamp_start", ""),
                        "timestamp_end": row.get("timestamp_end", ""),
                        "interface_name": row.get("interface_name", ""),
                        "interface_ip": row.get("interface_ip", ""),
                        "public_ip": row.get("public_ip", ""),
                        "macos_version": row.get("macos_version", ""),
                        "mac_model": row.get("mac_model", ""),
                        "server_host": row.get("server_host", ""),
                        "wifi_active": row.get("wifi_active", ""),
                        "router_tech": row.get("router_tech", ""),
                        "router_rsrp": row.get("router_rsrp", ""),
                        "router_rsrq": row.get("router_rsrq", ""),
                        "router_sinr": row.get("router_sinr", ""),
                        "router_band": row.get("router_band", ""),
                    })
        runs.sort(key=lambda r: r.get("timestamp_start", ""), reverse=True)
        self._json(runs)

    def _api_metrics(self, run_id: str) -> None:
        rows: list[dict] = []
        for fpath in _find_csvs(self.indir, "measurements_long.csv"):
            for row in _read_csv(fpath):
                if not run_id or row.get("run_id") == run_id:
                    rows.append(row)
        self._json(rows)

    def _api_system(self, run_id: str) -> None:
        rows: list[dict] = []
        for fpath in _find_csvs(self.indir, "system_metrics.csv"):
            for row in _read_csv(fpath):
                if not run_id or row.get("run_id") == run_id:
                    rows.append(row)
        self._json(rows)

    def _api_metadata(self, run_id: str) -> None:
        for fpath in _find_csvs(self.indir, "run_metadata.csv"):
            for row in _read_csv(fpath):
                if row.get("run_id") == run_id:
                    self._json(row)
                    return
        self._json({})

    def _api_location(self, run_id: str) -> None:
        """Return geolocation for the public IP stored in run_metadata."""
        public_ip = ""
        if run_id:
            for fpath in _find_csvs(self.indir, "run_metadata.csv"):
                for row in _read_csv(fpath):
                    if row.get("run_id") == run_id:
                        public_ip = row.get("public_ip", "")
                        break
                if public_ip:
                    break

        if not public_ip or public_ip in ("", "unknown"):
            self._json({"error": "No public IP", "lat": None, "lon": None})
            return

        try:
            url = f"http://ip-api.com/json/{public_ip}?fields=status,lat,lon,city,country,isp,org,query"
            with urllib.request.urlopen(url, timeout=5) as resp:
                data = json.loads(resp.read())
            self._json(data)
        except Exception as exc:
            self._json({"error": str(exc), "lat": None, "lon": None})


# ──────────────────────────────────────────────────────────────────────────────
# Server entry point
# ──────────────────────────────────────────────────────────────────────────────

def start_server(indir: Path, port: int = 8181, open_browser: bool = True) -> None:
    """Start the dashboard HTTP server and optionally open a browser."""
    DashboardHandler.indir = indir
    DashboardHandler.static_dir = Path(__file__).parent / "static"

    server = HTTPServer(("127.0.0.1", port), DashboardHandler)
    url = f"http://localhost:{port}"
    log.info("Dashboard running at %s  (results: %s)", url, indir)
    log.info("Press Ctrl+C to stop")

    if open_browser:
        import threading
        import webbrowser
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log.info("Dashboard stopped")
    finally:
        server.server_close()
