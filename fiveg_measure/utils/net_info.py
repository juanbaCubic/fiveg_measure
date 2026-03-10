"""
fiveg_measure/utils/net_info.py — Network interface and system information helpers.
"""
from __future__ import annotations

import logging
import platform
import socket
import subprocess
from datetime import datetime, timezone
from typing import Optional

import psutil

log = logging.getLogger(__name__)


def get_interface_info(iface: str) -> dict:
    """Return IP, gateway, MTU for the given interface."""
    info: dict = {
        "interface_name": iface,
        "interface_ip": "",
        "gateway": "",
        "mtu": "",
    }
    # IP address
    addrs = psutil.net_if_addrs()
    if iface in addrs:
        for addr in addrs[iface]:
            if addr.family == socket.AF_INET:
                info["interface_ip"] = addr.address
                break
    # MTU
    stats = psutil.net_if_stats()
    if iface in stats:
        info["mtu"] = stats[iface].mtu

    # Gateway — use `netstat -rn` on macOS
    try:
        res = subprocess.run(
            ["netstat", "-rn"],
            capture_output=True, text=True, timeout=10
        )
        for line in res.stdout.splitlines():
            parts = line.split()
            if len(parts) >= 6 and parts[0] == "default" and parts[-1] == iface:
                info["gateway"] = parts[1]
                break
        if not info["gateway"]:
            # fallback: first default route
            for line in res.stdout.splitlines():
                parts = line.split()
                if len(parts) >= 2 and parts[0] == "default":
                    info["gateway"] = parts[1]
                    break
    except Exception as exc:
        log.warning("Could not determine gateway: %s", exc)

    return info


def wifi_active() -> bool:
    """Return True if any Wi-Fi interface is up and has an IP."""
    wifi_ifaces = ["en0", "en1", "en2"]  # common macOS Wi-Fi names
    addrs = psutil.net_if_addrs()
    stats = psutil.net_if_stats()
    for iface in wifi_ifaces:
        if iface in stats and stats[iface].isup:
            for addr in addrs.get(iface, []):
                if addr.family == socket.AF_INET and addr.address:
                    return True
    return False


def get_public_ip(timeout: float = 5.0) -> str:
    """Try to get public IP from ifconfig.me."""
    try:
        import urllib.request
        with urllib.request.urlopen("https://ifconfig.me/ip", timeout=timeout) as resp:
            return resp.read().decode().strip()
    except Exception:
        return ""


def get_mac_model() -> str:
    """Return Mac model identifier (e.g. MacBookPro18,2)."""
    try:
        res = subprocess.run(
            ["system_profiler", "SPHardwareDataType"],
            capture_output=True, text=True, timeout=15,
        )
        for line in res.stdout.splitlines():
            if "Model Identifier" in line:
                return line.split(":")[-1].strip()
    except Exception:
        pass
    return ""


def now_iso(tz_name: Optional[str] = None) -> str:
    """Return current time as ISO 8601 string."""
    try:
        if tz_name:
            from zoneinfo import ZoneInfo
            dt = datetime.now(ZoneInfo(tz_name))
        else:
            dt = datetime.now(timezone.utc)
    except Exception:
        dt = datetime.now(timezone.utc)
    return dt.isoformat(timespec="seconds")


def macos_version() -> str:
    return platform.mac_ver()[0] or platform.version()
