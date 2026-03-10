# 🌿 Guía de Pruebas de Campo — La Mayora (R3)

> **Objetivo:** Validar los KPIs de comunicación 5G en condiciones operativas reales para el Report 3 (R3).  
> **Equipo necesario:** Portátil con `fiveg_measure`, Router NETGEAR MR6150 con SIM 5G, cable Ethernet, batería portátil.

---

## Fase 0: Preparación Previa (antes de salir)

- [ ] Verificar que `fiveg_measure` está instalado y funciona (`fiveg-measure --version`)
- [ ] Tener cargado el portátil y batería externa para el router
- [ ] Llevar cable Ethernet (conexión directa al router)
- [ ] Tener este documento accesible offline (PDF o copia local)
- [ ] VPN desactivada (mediremos conexión 5G directa)

---

## Fase 1: Configuración SIM y APN en el Router

### 1.1 Insertar la SIM

1. Apagar el router NETGEAR MR6150.
2. Insertar la tarjeta SIM proporcionada en La Mayora en la bandeja del router.
3. Encender el router y esperar ~2 minutos a que arranque completamente.

### 1.2 Configurar el APN

1. Conectar el portátil al Wi-Fi del router (SSID: `NETGEAR-MR6150-XXXX`) o por Ethernet.
2. Abrir el navegador: **http://192.168.1.1** (o la IP del router).
3. Iniciar sesión con las credenciales del router.
4. Ir a **Settings → Network → APN**.
5. Crear un nuevo perfil APN:
   - **Nombre del perfil:** `La Mayora 5G`
   - **APN:** *(el que proporcionen en La Mayora, probablemente `internet1` o similar)*
   - **Tipo de autenticación:** `None` (o según indicaciones)
   - **Tipo de IP:** `IPv4/IPv6`
6. Guardar y seleccionar el nuevo perfil como activo.
7. Verificar que el router muestra conexión 5G/LTE en la pantalla o el panel web.

### 1.3 Verificar Conectividad Básica

```bash
# Desactivar Wi-Fi del portátil (usar solo Ethernet al router)
networksetup -setairportpower en0 off

# Verificar IP asignada
ifconfig en6   # o la interfaz Ethernet correspondiente

# Ping al servidor de La Mayora
ping -c 10 10.34.1.31
```

> **⚠️ IMPORTANTE:** Si el ping falla, verificar que el APN es correcto y que el servidor está encendido. Contactar con el equipo de La Mayora.

---

## Fase 2: Validación de Conectividad con fiveg_measure

Una vez que el ping funciona, validar con el framework:

```bash
cd ~/MAYORA/fiveg_measure

# Verificar conexión SSH y herramientas
fiveg-measure remote-setup --config configs/conf_mayora.yaml

# Debe mostrar:
#   ssh_ok: True
#   iperf3_installed: True
```

Si todo está OK, ejecutar un **doctor** rápido:

```bash
fiveg-measure doctor --config configs/conf_mayora.yaml
```

> ✅ Si ssh_ok = True e iperf3_installed = True, pasamos a las pruebas.

---

## Fase 3: Pruebas en Site 1 — Micro-celda (Water Tank)

### Objetivo
Validar **uplink de vídeo HD** y medir la calidad radio en la zona más cercana a los cultivos.

### Métricas clave
- RSRP, RSRQ, SINR (calidad radio → correlación con Feko)
- Throughput uplink TCP (simula streaming de vídeo)
- Latencia E2E

### Procedimiento

1. Ubicarse en el **Site 1 (junto al Water Tank / micro-celda)**.
2. Anotar coordenadas GPS (foto del móvil con ubicación).
3. Anotar las métricas radio del router:
   - Acceder a **http://192.168.1.1 → Signal Info**
   - Apuntar: **RSRP**, **RSRQ**, **SINR**, **Banda**, **Cell ID**

4. Lanzar la suite completa:

```bash
fiveg-measure run-suite \
  --config configs/conf_mayora.yaml \
  --outdir results/site1_microcelda \
  --tag "Site1_MicroCelda_$(date +%Y%m%d_%H%M)" \
  --start-server
```

5. Mientras corre la suite (~10 min), tomar fotos del entorno y de la pantalla del router.

6. Al terminar, generar el resumen:

```bash
fiveg-measure summarize \
  --indir results/site1_microcelda \
  --out results/site1_microcelda/summary.csv \
  --config configs/conf_mayora.yaml
```

7. **Apuntar en la libreta:**
   - RSRP medido: ___ dBm  (Feko predice: ___ dBm)
   - SINR medido: ___ dB
   - Latencia P99: ___ ms
   - Throughput UL: ___ Mbps

---

## Fase 4: Pruebas en Site 2 — Macro-celda (Torre Telco)

### Objetivo
Verificar **cobertura general** y robustez de la conexión en toda la extensión de la finca.

### Procedimiento

1. Desplazarse al **Site 2 (zona de la torre de telecomunicaciones)**.
2. Repetir la captura de métricas radio (RSRP, SINR, etc.)

3. Lanzar la suite:

```bash
fiveg-measure run-suite \
  --config configs/conf_mayora.yaml \
  --outdir results/site2_macrocelda \
  --tag "Site2_MacroCelda_$(date +%Y%m%d_%H%M)" \
  --start-server
```

4. Generar resumen:

```bash
fiveg-measure summarize \
  --indir results/site2_macrocelda \
  --out results/site2_macrocelda/summary.csv \
  --config configs/conf_mayora.yaml
```

5. **Apuntar en la libreta:**
   - RSRP medido: ___ dBm  (Feko predice: ___ dBm)
   - SINR medido: ___ dB
   - Latencia P99: ___ ms
   - Throughput DL/UL: ___ Mbps

---

## Fase 5: Pruebas en Áreas de Vuelo (Líneas de Cultivo)

### Objetivo
Validación **operativa**: comprobar que la latencia E2E ≤ 50ms y PER ≤ 1% mientras se recorren las hileras de pitahaya (simula trayectoria de dron).

### Procedimiento

1. Ubicarse en el **inicio de una línea de cultivo** representativa.
2. Capturar métricas radio iniciales.

3. Lanzar la suite **mientras se recorre la hilera a pie** (simula movimiento del dron):

```bash
fiveg-measure run-suite \
  --config configs/conf_mayora.yaml \
  --outdir results/vuelo_linea1 \
  --tag "Vuelo_Linea1_$(date +%Y%m%d_%H%M)" \
  --start-server
```

4. **Repetir en al menos 2-3 líneas diferentes** para capturar variabilidad:

```bash
fiveg-measure run-suite \
  --config configs/conf_mayora.yaml \
  --outdir results/vuelo_linea2 \
  --tag "Vuelo_Linea2_$(date +%Y%m%d_%H%M)" \
  --start-server
```

5. Generar resúmenes:

```bash
fiveg-measure summarize \
  --indir results/vuelo_linea1 \
  --out results/vuelo_linea1/summary.csv \
  --config configs/conf_mayora.yaml

fiveg-measure summarize \
  --indir results/vuelo_linea2 \
  --out results/vuelo_linea2/summary.csv \
  --config configs/conf_mayora.yaml
```

6. **Verificar KPIs de aplicación:**
   - Latencia P99 ≤ 50 ms → ✅/❌
   - PER (loss_pct) ≤ 1% → ✅/❌
   - Throughput UL ≥ 15 Mbps → ✅/❌

---

## Fase 6: Pruebas en Zonas de Transición y Sombras

### Objetivo
Asegurar fiabilidad del sistema en **bordes de celda** y zonas con potencial degradación de señal.

### Procedimiento

1. Identificar **zonas de borde de cobertura** (donde el RSRP cae por debajo de -100 dBm).
2. Identificar **zonas de sombra** (detrás de edificios, arboleda densa, etc.)

3. En cada zona, lanzar una suite reducida o completa:

```bash
fiveg-measure run-suite \
  --config configs/conf_mayora.yaml \
  --outdir results/transicion_borde_celda \
  --tag "Transicion_BordeCelda_$(date +%Y%m%d_%H%M)" \
  --start-server
```

```bash
fiveg-measure run-suite \
  --config configs/conf_mayora.yaml \
  --outdir results/sombra_edificio \
  --tag "Sombra_Edificio_$(date +%Y%m%d_%H%M)" \
  --start-server
```

4. **Objetivo:** Documentar cómo degradan los KPIs en condiciones adversas.

---

## Fase 7: Resumen Global y Dashboard

Al finalizar todas las pruebas de campo, generar un resumen global:

```bash
# Ver todos los resultados en el dashboard
fiveg-measure dashboard --indir results/ --port 8181
```

### Estructura esperada de resultados:

```
results/
├── site1_microcelda/      ← Fase 3
├── site2_macrocelda/      ← Fase 4
├── vuelo_linea1/          ← Fase 5
├── vuelo_linea2/          ← Fase 5
├── vuelo_linea3/          ← Fase 5
├── transicion_borde_celda/ ← Fase 6
└── sombra_edificio/        ← Fase 6
```

---

## Checklist de Métricas Radio (rellenar en campo)

| Ubicación | RSRP (dBm) | RSRQ (dB) | SINR (dB) | Banda | Cell ID | Feko RSRP | Delta |
|:---|:---|:---|:---|:---|:---|:---|:---|
| Site 1 (Water Tank) | | | | | | | |
| Site 2 (Torre Telco) | | | | | | | |
| Línea vuelo 1 (inicio) | | | | | | | |
| Línea vuelo 1 (final) | | | | | | | |
| Línea vuelo 2 | | | | | | | |
| Borde de celda | | | | | | | |
| Zona de sombra | | | | | | | |

---

## Checklist de KPIs R3 — Validación Final

| KPI | Objetivo | Site 1 | Site 2 | Vuelo 1 | Vuelo 2 | Borde | Sombra |
|:---|:---|:---|:---|:---|:---|:---|:---|
| Latencia E2E (P99) | ≤ 50 ms | | | | | | |
| PER / Pérdida UDP | ≤ 1% | | | | | | |
| Throughput TCP UL | ≥ 15 Mbps | | | | | | |
| MEC Speed | ≤ 500 ms | | | | | | |
| Reliability | ≥ 99% | | | | | | |
| Correlación Feko (Δ RSRP) | ≤ 6 dB | | | | | | |

---

## Notas Importantes

> [!WARNING]
> **Antes de cada run**, desactivar el Wi-Fi del portátil para asegurar que todo el tráfico pasa por la conexión 5G del router.

> [!TIP]
> Hacer **fotos de la pantalla del router** con las métricas de señal y del entorno en cada punto de medición. Estas fotos servirán como evidencia para el R3.

> [!IMPORTANT]
> Si la batería del router se agota, los resultados parciales se conservan en la carpeta de salida. Puedes reanudar con un nuevo `--tag` sin perder datos anteriores.
