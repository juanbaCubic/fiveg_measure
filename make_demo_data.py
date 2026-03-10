"""
Genera datos de demostración para el dashboard fiveg_measure.
Uso: python3 make_demo_data.py
"""
import csv, uuid, datetime, pathlib, math, random

outdir = pathlib.Path('results/demo')
outdir.mkdir(parents=True, exist_ok=True)
run_id = str(uuid.uuid4())

def ts(s=0):
    return (datetime.datetime(2026, 3, 4, 16, 30, 0,
        tzinfo=datetime.timezone.utc) + datetime.timedelta(seconds=s)).isoformat()

random.seed(42)

# ── run_metadata.csv ──────────────────────────────────────────────────────────
meta_fields = [
    'run_id','tag','timestamp_start','timestamp_end','macos_version','mac_model',
    'interface_name','interface_ip','gateway','mtu','wifi_active','public_ip',
    'server_host','iperf_port','router_tech','router_rsrp','router_rsrq',
    'router_sinr','router_band','router_cell_id',
]
with open(outdir / 'run_metadata.csv', 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=meta_fields)
    w.writeheader()
    w.writerow({
        'run_id': run_id, 'tag': 'demo_5G_casa',
        'timestamp_start': ts(0), 'timestamp_end': ts(300),
        'macos_version': '15.3', 'mac_model': 'MacBookPro18,2',
        'interface_name': 'en5', 'interface_ip': '192.168.1.50',
        'gateway': '192.168.1.1', 'mtu': 1500, 'wifi_active': 'False',
        'public_ip': '85.58.22.101', 'server_host': '192.168.1.100',
        'iperf_port': 5201, 'router_tech': '5G-NR',
        'router_rsrp': '-82', 'router_rsrq': '-11', 'router_sinr': '19',
        'router_band': 'n77', 'router_cell_id': '12345678',
    })

# ── measurements_long.csv ─────────────────────────────────────────────────────
tests = [
    ('ping',        'rtt_ms',            'ms',   'NA',  18,  4),
    ('ping',        'loss_pct',          '%',    'NA',  0.4, 0.15),
    ('iperf_tcp',   'throughput_mbps',   'Mbps', 'UL',  115, 20),
    ('iperf_tcp',   'throughput_mbps',   'Mbps', 'DL',  210, 30),
    ('iperf_udp',   'jitter_ms',         'ms',   'UL',  1.1, 0.4),
    ('iperf_udp',   'loss_pct',          '%',    'UL',  0.2, 0.1),
    ('tcp_connect', 'connect_time_ms',   'ms',   'NA',  24,  5),
    ('bufferbloat', 'rtt_idle_p50',      'ms',   'NA',  18,  2),
    ('bufferbloat', 'rtt_load_p50',      'ms',   'NA',  47,  8),
    ('bufferbloat', 'rtt_increase_ms',   'ms',   'NA',  29,  7),
]
long_rows = []
for tn, mn, unit, d, base, scale in tests:
    for i, s in enumerate(range(0, 300, 10)):
        wave = 3 * math.sin(i / 3) if 'rtt' in mn else 0
        v = max(0.0, base + random.gauss(0, scale) + wave)
        long_rows.append({
            'run_id': run_id, 'test_id': str(uuid.uuid4()),
            'test_name': tn, 'iteration': (i // 3) + 1,
            'timestamp': ts(s), 'metric_name': mn,
            'metric_value': round(v, 3), 'unit': unit,
            'direction': d, 'notes': '',
        })

with open(outdir / 'measurements_long.csv', 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=long_rows[0].keys())
    w.writeheader()
    w.writerows(long_rows)

# ── system_metrics.csv ────────────────────────────────────────────────────────
tx, rx = 0, 0
sys_rows = []
for s in range(0, 300):
    tx += random.randint(50_000, 150_000)
    rx += random.randint(300_000, 1_500_000)
    sys_rows.append({
        'run_id': run_id, 'test_id': '', 'timestamp': ts(s),
        'cpu_percent': round(max(0, 18 + random.gauss(0, 4) + 8 * math.sin(s / 30)), 1),
        'mem_used_mb': round(4100 + random.gauss(0, 60), 1),
        'net_bytes_sent': tx, 'net_bytes_recv': rx,
    })

with open(outdir / 'system_metrics.csv', 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=sys_rows[0].keys())
    w.writeheader()
    w.writerows(sys_rows)

print(f"Demo data written to {outdir}")
print(f"run_id: {run_id}")
print(f"Files: {[p.name for p in sorted(outdir.iterdir())]}")
