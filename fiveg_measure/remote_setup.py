"""
fiveg_measure/remote_setup.py — SSH-based remote server management (iperf3).
"""
from __future__ import annotations

import logging
import time
from pathlib import Path

import paramiko

from .config import Config

log = logging.getLogger(__name__)


class RemoteServer:
    """SSH connection to the remote Linux server."""

    def __init__(self, cfg: Config):
        self._cfg = cfg
        self._client: paramiko.SSHClient | None = None
        self._iperf_pid: int | None = None

    def connect(self) -> None:
        host = self._cfg.server["host"]
        port = self._cfg.server.get("ssh_port", 22)
        user = self._cfg.server.get("ssh_user", "ubuntu")
        password = self._cfg.ssh_password
        
        # Only use a key if it was EXPLICITLY set in the user's config
        # (not just the default value from _DEFAULTS)
        user_set_key = self._cfg.server.get("ssh_key_path", "")
        has_explicit_key = bool(user_set_key) and user_set_key != "~/.ssh/id_rsa"
        
        log.info("[remote_setup] Connecting to %s@%s:%d", user, host, port)
        self._client = paramiko.SSHClient()
        self._client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        connect_kwargs = {
            "hostname": host,
            "port": port,
            "username": user,
            "timeout": 30,
            "look_for_keys": False,
            "allow_agent": False,
        }
        
        if password:
            # Password takes priority
            connect_kwargs["password"] = password
            log.info("[remote_setup] Using password authentication")
        elif has_explicit_key:
            key_path = self._cfg.ssh_key_path
            if key_path and key_path.exists():
                connect_kwargs["key_filename"] = str(key_path)
                log.info("[remote_setup] Using key authentication: %s", key_path)
            else:
                log.warning("[remote_setup] Key file not found: %s", user_set_key)
        else:
            # Fallback: let paramiko try default keys
            connect_kwargs["look_for_keys"] = True
            
        self._client.connect(**connect_kwargs)
        log.info("[remote_setup] Connected")

    def disconnect(self) -> None:
        if self._client:
            self._client.close()
            self._client = None

    def _exec(self, cmd: str, timeout: float = 30) -> tuple[str, str, int]:
        """Execute a command over SSH, return (stdout, stderr, exit_code)."""
        if not self._client:
            raise RuntimeError("Not connected")
        _, stdout, stderr = self._client.exec_command(cmd, timeout=timeout)
        exit_code = stdout.channel.recv_exit_status()
        return stdout.read().decode(), stderr.read().decode(), exit_code

    def check_iperf3(self) -> bool:
        """Return True if iperf3 is installed on the server."""
        out, _, rc = self._exec("which iperf3 || command -v iperf3")
        installed = rc == 0 and bool(out.strip())
        log.info("[remote_setup] iperf3 installed on server: %s", installed)
        return installed

    def install_iperf3(self) -> bool:
        """Try to install iperf3 via apt/yum. Returns success."""
        log.info("[remote_setup] Attempting iperf3 install (apt)...")
        out, err, rc = self._exec(
            "sudo apt-get install -y iperf3 2>&1 || sudo yum install -y iperf3 2>&1",
            timeout=120,
        )
        if rc == 0:
            log.info("[remote_setup] iperf3 installed successfully")
            return True
        log.error("[remote_setup] Install failed: %s", err)
        return False

    def start_iperf_server(self, port: int = 5201) -> bool:
        """Start iperf3 server in background on the remote host. Returns True if started."""
        if not self._client:
            raise RuntimeError("Not connected")
        # Kill any existing iperf3 server
        self._exec("pkill -f 'iperf3 -s' 2>/dev/null || true")
        time.sleep(1)
        # Start in background, capture PID
        out, err, rc = self._exec(
            f"nohup iperf3 -s -p {port} --daemon 2>/dev/null; "
            f"sleep 0.5; pgrep -n iperf3"
        )
        pid_str = out.strip().split()[-1] if out.strip() else ""
        if pid_str.isdigit():
            self._iperf_pid = int(pid_str)
            log.info("[remote_setup] iperf3 server started (pid=%d, port=%d)", self._iperf_pid, port)
            return True
        log.warning("[remote_setup] Could not confirm iperf3 server start. stderr: %s", err)
        return False

    def stop_iperf_server(self) -> None:
        """Stop the iperf3 server on the remote host."""
        log.info("[remote_setup] Stopping iperf3 server")
        if self._iperf_pid:
            self._exec(f"kill {self._iperf_pid} 2>/dev/null || true")
            self._iperf_pid = None
        else:
            self._exec("pkill -f 'iperf3 -s' 2>/dev/null || true")

    def verify(self) -> dict:
        """Run full verification; return dict of results."""
        results: dict = {}
        try:
            self.connect()
            results["ssh_ok"] = True
            results["iperf3_installed"] = self.check_iperf3()
            out, _, _ = self._exec("uname -a")
            results["uname"] = out.strip()
            out, _, _ = self._exec("free -h 2>/dev/null || vm_stat")
            results["memory"] = out.strip()[:100]
        except Exception as exc:
            results["ssh_ok"] = False
            results["error"] = str(exc)
        finally:
            self.disconnect()
        return results
