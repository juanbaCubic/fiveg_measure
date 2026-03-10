# fiveg_measure

**Framework de medición de comunicaciones 5G para macOS vía Ethernet.**

CLI completo para medir latencia, throughput TCP/UDP, jitter, bufferbloat y HTTP desde un MacBook Pro conectado por Ethernet a un router 5G (NETGEAR MR6150) contra un servidor Linux remoto.

---

## Estructura del proyecto

```
fiveg_measure/
├── fiveg_measure/
│   ├── cli.py               # Punto de entrada CLI
│   ├── config.py            # Carga y validación de config YAML
│   ├── runner.py            # Orquestador de la suite de tests
│   ├── remote_setup.py      # Gestión SSH del servidor remoto (paramiko)
│   ├── tests/
│   │   ├── ping_test.py         # ICMP ping → ping.csv, ping_summary.csv
│   │   ├── tcp_connect_test.py  # TCP connect latency → tcp_connect.csv
│   │   ├── traceroute_test.py   # Traceroute → traceroute.csv
│   │   ├── mtr_test.py          # MTR → mtr.csv
│   │   ├── iperf_tcp_test.py    # iPerf3 TCP UL/DL → iperf_tcp_*.csv
│   │   ├── iperf_udp_test.py    # iPerf3 UDP → iperf_udp_summary.csv
│   │   ├── bufferbloat_test.py  # Bufferbloat → bufferbloat*.csv
│   │   ├── http_upload_test.py  # HTTP upload / SCP → http_transfer.csv
│   │   ├── http_download_test.py# HTTP download → http_transfer.csv
│   │   ├── metadata_probe.py    # run_metadata.csv + system_metrics.csv
│   │   └── router_probe.py      # Probe opcional MR6150 (campos vacíos si no disponible)
│   ├── utils/               # logging, subprocess, CSV writer, net_info
│   └── schemas/
│       └── csv_schemas.md   # Definición de columnas de todos los CSVs
├── pyproject.toml
├── example_config.yaml      # Plantilla de configuración lista para editar
├── make_sample_data.sh      # Genera ficheros de prueba 50MB/200MB
└── README.md
```

---

## Instalación

### 1. Prerequisitos en el Mac

```bash
# Homebrew tools
brew install iperf3 mtr

# Opcional para tests de streaming
brew install ffmpeg

# Python dependencies
pip install pandas pyyaml paramiko psutil requests
```

### 2. Instalar el framework

```bash
cd /path/to/fiveg_measure
pip install -e .
```

Esto registra el comando `fiveg-measure` en tu PATH.

### 3. Prerequisitos en el servidor remoto (Linux)

```bash
# Ubuntu/Debian
sudo apt-get install -y iperf3

# CentOS/RHEL
sudo yum install -y iperf3

# Arrancar el servidor iperf3:
iperf3 -s -p 5201 --daemon

# Para tests de descarga HTTP:
mkdir ~/http_files
cd ~/http_files
python3 -m http.server 8080 &
```

### 4. Verificar instalación del servidor via SSH

```bash
fiveg-measure remote-setup --config example_config.yaml
# Con instalar automáticamente si no está:
fiveg-measure remote-setup --config example_config.yaml --install
```

---

## Configuración

Copia y edita `example_config.yaml`:

```bash
cp example_config.yaml my_config.yaml
# Edita: server.host, server.ssh_user, server.ssh_key_path, client.interface
nano my_config.yaml
```

**Campos obligatorios:**
- `server.host` — IP o hostname del servidor Linux
- `server.ssh_user` + `server.ssh_key_path` — acceso SSH
- `client.interface` — interfaz Ethernet (`ifconfig` para ver el nombre exacto: `en0`, `en5`, etc.)

**Control del router (opcional):**
Si tienes los valores LTE/5G del MR6150 (puedes verlos en la UI web del router en `192.168.1.1`), añádelos al config:

```yaml
router_manual:
  tech: "5G-NR"
  rsrp: -85
  rsrq: -12
  sinr: 18
  band: "n77"
  cell_id: "12345678"
```

---

## Uso

### Doctor — verificar prerequisitos

```bash
fiveg-measure doctor --config configs/my_config.yaml --outdir results/
```

Comprueba: herramientas instaladas, conectividad, interfaz Ethernet, Wi-Fi activo.
Genera: `results/doctor.csv`

### Suite completa

```bash
# Sin gestión automática del servidor iperf:
# (asegúrate de que iperf3 -s está corriendo en el servidor)
fiveg-measure run-suite --config configs/my_config.yaml --outdir results/ --tag "casa_test_01"

# Con arranque automático del servidor iperf vía SSH:
fiveg-measure run-suite --config configs/my_config.yaml --outdir results/ --tag "campo_5G" --start-server
```

**CSVs generados:**
```
results/
├── run_metadata.csv          # Metadatos del run
├── system_metrics.csv        # CPU/mem/net cada segundo
├── ping.csv + ping_summary.csv
├── tcp_connect.csv
├── traceroute.csv
├── mtr.csv
├── iperf_tcp_intervals.csv + iperf_tcp_summary.csv
├── iperf_udp_summary.csv
├── bufferbloat.csv + bufferbloat_summary.csv
├── http_transfer.csv
├── measurements_long.csv     # Formato long-form unificado
└── raw/                      # JSONs de iperf3, txt de ping, etc.
```

### Test individual

```bash
fiveg-measure run-test ping --config my_config.yaml --outdir results/
fiveg-measure run-test iperf_tcp --config my_config.yaml --outdir results/
fiveg-measure run-test bufferbloat --config my_config.yaml --outdir results/
```

Tests disponibles: `ping`, `tcp_connect`, `traceroute`, `mtr`, `iperf_tcp`, `iperf_udp`, `bufferbloat`, `http_upload`, `http_download`

### Resumen estadístico

```bash
fiveg-measure summarize --indir results/ --out summary.csv
```

Genera percentiles (p50/p90/p99), medias, min/max para cada métrica.

---

## Generar ficheros de prueba para HTTP/SCP

```bash
bash make_sample_data.sh
# Crea: sample_data/file_50mb.bin, sample_data/file_200mb.bin
```

Luego sube `file_200mb.bin` al servidor y sírvelo con Python HTTP:

```bash
scp sample_data/file_200mb.bin ubuntu@192.168.1.100:~/http_files/
ssh ubuntu@192.168.1.100 'cd ~/http_files && python3 -m http.server 8080 &'
```

---

## Ejemplo de ejecución completa (desde cero)

```bash
# 1. Instalar
brew install iperf3 mtr
pip install -e .

# 2. Configurar
cp example_config.yaml my_config.yaml
# Editar: server.host, ssh_user, ssh_key_path, client.interface

# 3. Comprobar
fiveg-measure doctor --config my_config.yaml

# 4. Generar datos de prueba
bash make_sample_data.sh

# 5. Ejecutar suite (el servidor debe tener iperf3 corriendo)
fiveg-measure run-suite \
  --config my_config.yaml \
  --outdir results/run_$(date +%Y%m%d_%H%M%S)/ \
  --tag "home_5G_test_01" \
  --start-server

# 6. Resumen
fiveg-measure summarize --indir results/ --out summary.csv
```

---

## Reproducibilidad

- Cada suite genera un `run_id` (UUID) único y un `tag` definido por el usuario.
- Cada test individual genera su propio `test_id` (UUID).
- Todos los timestamps son ISO 8601 con zona horaria configurable.
- Los raw outputs (JSON de iperf3, txt de ping, etc.) se guardan en `raw/` para re-parsear si es necesario.
- Logs detallados disponibles con `--log-level DEBUG --log-file session.log`.

---

## Notas sobre el NETGEAR MR6150

El MR6150 no expone una API REST pública documentada. Las opciones para capturar señal (RSRP/RSRQ/SINR/banda):

1. **Manual:** leer los valores desde la UI web (`http://192.168.1.1`) y añadirlos en `router_manual:` del config.
2. **Automático (especulativo):** el módulo `router_probe.py` intenta endpoints locales del tipo `/api/v1/lte_info`. Si el firmware del router los expone, se capturarán automáticamente.
3. **Futuro:** algunos usuarios usan Telnet/serial al módulo LTE del router para extraer AT commands — esto queda fuera del scope actual.

---

## Esquemas CSV

Ver [`fiveg_measure/schemas/csv_schemas.md`](fiveg_measure/schemas/csv_schemas.md) para la definición completa de columnas de todos los CSVs.
