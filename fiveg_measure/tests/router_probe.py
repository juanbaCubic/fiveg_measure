"""
fiveg_measure/tests/router_probe.py — Optional NETGEAR MR6150 status probe.

The MR6150 does not expose a public documented REST API. This module attempts
to query well-known local endpoints for signal information. If the router
is not reachable or the endpoint is unavailable, all fields return empty strings.

To fill these fields manually, add them to your config under:

  router_manual:
    tech: "5G-NR"
    rsrp: -85
    rsrq: -12
    sinr: 18
    band: "n77"
    cell_id: "12345678"
"""
from __future__ import annotations

import logging
from typing import Any

log = logging.getLogger(__name__)

_EMPTY = {"tech": "", "rsrp": "", "rsrq": "", "sinr": "", "band": "", "cell_id": ""}


def probe(cfg) -> dict[str, Any]:
    """Try to probe the MR6150. Returns signal info dict (may be all empty)."""
    # ── 1. Check for manual override in config ────────────────────────────────
    manual = cfg.raw.get("router_manual", {})
    if manual:
        log.info("[router_probe] Using manually configured router values")
        result = dict(_EMPTY)
        result.update({k: v for k, v in manual.items() if k in _EMPTY})
        return result

    # ── 2. Try known NETGEAR local gateway endpoints ──────────────────────────
    # The MR6150 uses a web UI at 192.168.1.1 (default).
    # It does not have a public REST API, but some firmware versions expose
    # SOAP-like endpoints or JSON pages. Attempt a GET to the status endpoint.
    gateway = cfg.raw.get("client", {}).get("router_ip", "192.168.1.1")
    urls_to_try = [
        f"http://{gateway}/api/v1/lte_info",   # speculative
        f"http://{gateway}/cellular_status",    # speculative
    ]

    try:
        import urllib.request
        for url in urls_to_try:
            try:
                with urllib.request.urlopen(url, timeout=2) as resp:
                    import json
                    data = json.loads(resp.read())
                    log.info("[router_probe] Got data from %s", url)
                    return {
                        "tech": data.get("technology", data.get("rat", "")),
                        "rsrp": data.get("rsrp", ""),
                        "rsrq": data.get("rsrq", ""),
                        "sinr": data.get("sinr", ""),
                        "band": data.get("band", ""),
                        "cell_id": data.get("cell_id", data.get("cellID", "")),
                    }
            except Exception:
                continue
    except Exception as exc:
        log.debug("[router_probe] probe failed: %s", exc)

    log.debug("[router_probe] No data available — fields will be empty. "
              "Add 'router_manual:' to your config to set values manually.")
    return dict(_EMPTY)
