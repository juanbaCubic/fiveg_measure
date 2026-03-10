# CSV Schema Definitions — fiveg_measure

This document defines the columns of every CSV produced by the framework.

---

## run_metadata.csv

| Column | Type | Description |
|--------|------|-------------|
| run_id | UUID | Unique run identifier |
| tag | string | Human-readable tag passed via --tag |
| timestamp_start | ISO 8601 | Suite start time |
| timestamp_end | ISO 8601 | Suite end time |
| macos_version | string | macOS version string |
| mac_model | string | Mac hardware model identifier |
| interface_name | string | Ethernet interface (e.g. en5) |
| interface_ip | string | IP address on that interface |
| gateway | string | Default gateway IP |
| mtu | integer | MTU in bytes |
| wifi_active | bool | True if any Wi-Fi interface is up |
| public_ip | string | Public IP (from ifconfig.me) or empty |
| server_host | string | Remote server hostname/IP |
| iperf_port | integer | iperf3 port used |
| router_tech | string | Technology (5G-NR/LTE/empty) |
| router_rsrp | string | RSRP in dBm (or empty) |
| router_rsrq | string | RSRQ in dB (or empty) |
| router_sinr | string | SINR in dB (or empty) |
| router_band | string | Band identifier (or empty) |
| router_cell_id | string | Cell ID (or empty) |

---

## system_metrics.csv

| Column | Type | Description |
|--------|------|-------------|
| run_id | UUID | |
| test_id | UUID | Active test at sample time (or empty) |
| timestamp | ISO 8601 | |
| cpu_percent | float | CPU usage 0–100% |
| mem_used_mb | float | Physical memory used (MB) |
| net_bytes_sent | integer | Cumulative bytes sent (psutil) |
| net_bytes_recv | integer | Cumulative bytes received (psutil) |

---

## ping.csv

| Column | Type | Description |
|--------|------|-------------|
| run_id | UUID | |
| test_id | UUID | |
| iteration | integer | |
| timestamp | ISO 8601 | |
| seq | integer | ICMP sequence number (-1 = lost) |
| rtt_ms | float | Round-trip time (null if lost) |
| ttl | integer | |
| bytes | integer | |
| lost | bool | True if packet was lost |

## ping_summary.csv

Per-iteration summary: count, lost, loss_pct, rtt_min_ms, rtt_max_ms, rtt_avg_ms, rtt_p50_ms, rtt_stdev_ms.

---

## tcp_connect.csv

| Column | Type | Description |
|--------|------|-------------|
| run_id | UUID | |
| test_id | UUID | |
| iteration | integer | |
| timestamp | ISO 8601 | |
| host | string | |
| port | integer | |
| connect_time_ms | float | Time to complete TCP handshake |
| success | bool | |
| error | string | Error message if failed |

---

## traceroute.csv

| Column | Type | Description |
|--------|------|-------------|
| run_id | UUID | |
| test_id | UUID | |
| iteration | integer | |
| timestamp | ISO 8601 | |
| hop | integer | Hop number (1-based) |
| hop_ip | string | Router IP at this hop |
| rtt1_ms | float | First probe RTT |
| rtt2_ms | float | Second probe RTT |
| rtt3_ms | float | Third probe RTT |

---

## mtr.csv

| Column | Type | Description |
|--------|------|-------------|
| run_id | UUID | |
| test_id | UUID | |
| iteration | integer | |
| timestamp | ISO 8601 | |
| hop | integer | |
| hop_ip | string | |
| loss_pct | float | Packet loss % |
| last_ms | float | Last RTT |
| avg_ms | float | Average RTT |
| best_ms | float | Minimum RTT |
| wrst_ms | float | Maximum RTT |
| stdev_ms | float | RTT std deviation |

---

## iperf_tcp_intervals.csv

| Column | Type | Description |
|--------|------|-------------|
| run_id | UUID | |
| test_id | UUID | |
| iteration | integer | |
| timestamp | ISO 8601 | Test start |
| direction | UL/DL | |
| streams | integer | Number of parallel streams |
| interval_start_s | float | |
| interval_end_s | float | |
| bps | float | Bits per second |
| mbps | float | Megabits per second |
| retransmits | integer | TCP retransmits in interval |
| rtt_ms | float | Smoothed RTT (if available) |

## iperf_tcp_summary.csv

Per-combo summary: avg_mbps, p90_mbps, retransmits_total, error.

---

## iperf_udp_summary.csv

| Column | Type | Description |
|--------|------|-------------|
| run_id | UUID | |
| test_id | UUID | |
| iteration | integer | |
| timestamp | ISO 8601 | |
| bitrate_mbps | integer | Requested target bitrate |
| duration_s | integer | |
| jitter_ms | float | UDP jitter |
| lost_packets | integer | |
| total_packets | integer | |
| loss_pct | float | |
| out_of_order | integer | |
| avg_mbps | float | Actual achieved throughput |
| error | string | |

---

## bufferbloat.csv

| Column | Type | Description |
|--------|------|-------------|
| run_id | UUID | |
| test_id | UUID | |
| iteration | integer | |
| timestamp | ISO 8601 | |
| phase | idle/load | Measurement phase |
| rtt_ms | float | Ping RTT during phase |

## bufferbloat_summary.csv

Per-iteration: rtt_idle_p50, rtt_idle_avg, rtt_load_p50, rtt_load_avg, rtt_load_p95, rtt_increase_ms, idle_samples, load_samples.

---

## http_transfer.csv

| Column | Type | Description |
|--------|------|-------------|
| run_id | UUID | |
| test_id | UUID | |
| iteration | integer | |
| timestamp | ISO 8601 | |
| direction | upload/download | |
| url | string | |
| bytes | integer | |
| duration_ms | float | |
| throughput_mbps | float | |
| http_status | integer | HTTP status code (0 = SCP) |
| error | string | |

---

## measurements_long.csv (unified long-form)

| Column | Type | Description |
|--------|------|-------------|
| run_id | UUID | |
| test_id | UUID | |
| test_name | string | e.g. ping, iperf_tcp |
| iteration | integer | |
| timestamp | ISO 8601 | |
| metric_name | string | e.g. rtt_ms, throughput_mbps |
| metric_value | float | |
| unit | string | ms, Mbps, %, etc. |
| direction | UL/DL/NA | |
| notes | string | Extra context |

---

## doctor.csv

| Column | Type | Description |
|--------|------|-------------|
| check | string | Check name |
| status | OK/FAIL | |
| detail | string | |
| timestamp | ISO 8601 | |

---

## summary.csv (generated by `summarize` command)

| Column | Type | Description |
|--------|------|-------------|
| test_name | string | |
| metric_name | string | |
| direction | string | |
| unit | string | |
| count | integer | Number of samples |
| mean | float | |
| median | float | |
| p50 | float | |
| p90 | float | |
| p99 | float | |
| min | float | |
| max | float | |
| stdev | float | |
