"""
fiveg_measure/runner.py — Suite orchestration: runs all tests, manages warmup/cooldown.
"""
from __future__ import annotations

import logging
import signal
import time
import uuid
from pathlib import Path
from typing import Any

from .config import Config
from .tests.metadata_probe import SystemMetricsCollector, collect_run_metadata

log = logging.getLogger(__name__)

# Registry of all available tests (name -> module path suffix)
ALL_TESTS: list[str] = [
    "ping",
    "tcp_connect",
    "traceroute",
    "mtr",
    "iperf_tcp",
    "iperf_udp",
    "bufferbloat",
    "http_upload",
    "http_download",
    "mec",
]

_TEST_MODULE_MAP = {
    "ping": "fiveg_measure.tests.ping_test",
    "tcp_connect": "fiveg_measure.tests.tcp_connect_test",
    "traceroute": "fiveg_measure.tests.traceroute_test",
    "mtr": "fiveg_measure.tests.mtr_test",
    "iperf_tcp": "fiveg_measure.tests.iperf_tcp_test",
    "iperf_udp": "fiveg_measure.tests.iperf_udp_test",
    "bufferbloat": "fiveg_measure.tests.bufferbloat_test",
    "http_upload": "fiveg_measure.tests.http_upload_test",
    "http_download": "fiveg_measure.tests.http_download_test",
    "mec": "fiveg_measure.tests.mec_test",
}


def _import_test(name: str):
    import importlib
    module_path = _TEST_MODULE_MAP.get(name)
    if not module_path:
        raise ValueError(f"Unknown test: {name!r}. Available: {list(_TEST_MODULE_MAP)}")
    return importlib.import_module(module_path)


class SuiteRunner:
    def __init__(self, cfg: Config, outdir: Path, tag: str = "", run_id: str | None = None):
        self._cfg = cfg
        self._outdir = outdir
        self._tag = tag
        self._run_id = run_id or str(uuid.uuid4())
        self._aborted = False
        self._metrics_collector: SystemMetricsCollector | None = None

        # Handle Ctrl+C gracefully
        signal.signal(signal.SIGINT, self._handle_sigint)
        signal.signal(signal.SIGTERM, self._handle_sigint)

    def _handle_sigint(self, signum, frame):
        log.warning("Interrupted! Writing partial results...")
        self._aborted = True

    def run_suite(self, tests: list[str] | None = None) -> None:
        """Run all (or a subset of) tests for the configured number of iterations."""
        cfg = self._cfg
        outdir = self._outdir
        outdir.mkdir(parents=True, exist_ok=True)

        selected_tests = tests or ALL_TESTS

        # Collect run metadata
        meta = collect_run_metadata(cfg, self._run_id, self._tag, outdir)

        # Start system metrics collection
        self._metrics_collector = SystemMetricsCollector(cfg, outdir, self._run_id)
        self._metrics_collector.start()

        iterations = cfg.suite.get("iterations", 3)
        warmup = cfg.suite.get("warmup_seconds", 2)
        cooldown = cfg.suite.get("cooldown_seconds", 3)

        try:
            for iteration in range(1, iterations + 1):
                if self._aborted:
                    break
                log.info("═══ Iteration %d/%d ═══", iteration, iterations)
                for test_name in selected_tests:
                    if self._aborted:
                        break
                    log.info("── Starting test: %s (iter %d)", test_name, iteration)
                    if warmup > 0:
                        time.sleep(warmup)
                    try:
                        mod = _import_test(test_name)
                        mod.run(cfg, outdir, self._run_id, iteration)
                    except Exception as exc:
                        log.error("Test %s failed: %s", test_name, exc, exc_info=True)
                    finally:
                        if cooldown > 0 and not self._aborted:
                            time.sleep(cooldown)

        finally:
            if self._metrics_collector:
                self._metrics_collector.stop()

            # Update end timestamp in metadata
            from .utils import now_iso
            tz = cfg.output.get("timezone", "UTC")
            meta["timestamp_end"] = now_iso(tz)
            from .utils import write_rows
            write_rows(outdir / "run_metadata.csv", [meta], delimiter=cfg.output.get("csv_delimiter", ","))

            if self._aborted:
                log.warning("Suite aborted — partial results written to %s", outdir)
            else:
                log.info("Suite complete — results in %s", outdir)

    def run_single(self, test_name: str, iteration: int = 1) -> None:
        """Run a single test once."""
        outdir = self._outdir
        outdir.mkdir(parents=True, exist_ok=True)

        log.info("Running single test: %s", test_name)
        try:
            mod = _import_test(test_name)
            mod.run(self._cfg, outdir, self._run_id, iteration)
        except Exception as exc:
            log.error("Test %s failed: %s", test_name, exc, exc_info=True)
