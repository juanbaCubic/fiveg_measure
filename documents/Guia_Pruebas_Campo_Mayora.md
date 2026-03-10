# 🌿 Guía de Pruebas de Campo — La Mayora (R3)

> **Objetivo:** Validar los KPIs de comunicación 5G en condiciones operativas reales para el Report 3 (R3), cerrando el bucle con la simulación del Gemelo Digital (Altair Feko + Open5GS).  
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

## Fase 3: Baseline — Antena Física Real

### Objetivo
Establecer el **baseline de rendimiento idóneo** para la red basándonos en la instalación física real. Según las especificaciones de Altair Feko (página 26), la antena sectorial está montada con las siguientes características:
- **Ubicación exacta:** 36° 45′ 31.56″ N, 4° 2′ 32.31″ W
- **Acimut de máxima radiación:** 25°
- **Altura sobre el terreno:** 5.65 m (Cota 75 m)
- **Potencia esperada (Feko) en la zona objetivo a 150m:** ~ -55 dBm

### Métricas clave
- RSRP, RSRQ, SINR: deben coincidir empíricamente con la previsión de alta eficiencia de Feko (-55 dBm).
- Throughput uplink TCP óptimo y Latencia mínima.

### Procedimiento

1. Ubícate lo más cerca posible de la **Antena Física Real (36° 45′ 31.56″ N, 4° 2′ 32.31″ W)**, posicionándote en la dirección del acimut **25°** (hacia la zona de cultivo verde).
2. Anotar las métricas radio del router (para constatar pérdidas por espacio libre):
   - Acceder a **http://192.168.1.1 → Signal Info**
   - Apuntar: **RSRP**, **RSRQ**, **SINR**, **Banda**, **Cell ID**

3. Lanzar la suite completa:

```bash
fiveg-measure run-suite \
  --config configs/conf_mayora.yaml \
  --outdir results/fase3_baseline_antena \
  --tag "Fase3_Baseline_Antena_$(date +%Y%m%d_%H%M)" \
  --start-server
```

4. Mientras corre la suite (~10 min), tomar fotos que documenten la línea de visión directa entre el router y la antena en el acimut 25°.

5. Al terminar, generar el resumen:

```bash
fiveg-measure summarize \
  --indir results/fase3_baseline_antena \
  --out results/fase3_baseline_antena/summary.csv \
  --config configs/conf_mayora.yaml
```

6. **Apuntar en la libreta:**
   - RSRP medido cerca de antena: ___ dBm  
   - Latencia P99: ___ ms
---

## Fase 4: Pruebas Operativas de Vuelo — Zona de Plantación (Zona Verde)

### Objetivo
Validación **operativa** sobre trayectorias del dron. En esta zona verde (geográficamente alrededor de **36°45'32.9"N 4°02'27.8"W**) el robot necesita asegurar una latencia E2E ≤ 50ms y PER ≤ 1% para la transmisión de vídeo a Edge.

### Procedimiento

1. Dirígete a la **Zona Verde de plantación** (coord: **36°45'32.9"N 4°02'27.8"W**) alineado con la trayectoria de máxima radiación (**acimut 25°** del emplezamiento 1).
2. Capturar métricas radio iniciales.

3. Lanzar la suite **mientras caminas lentamente por las hileras** (simulando avance del robot):

```bash
fiveg-measure run-suite \
  --config configs/conf_mayora.yaml \
  --outdir results/fase4_vuelo_plantacion \
  --tag "Fase4_Vuelo_Plantacion_$(date +%Y%m%d_%H%M)" \
  --start-server
```

4. Generar resumen:

```bash
fiveg-measure summarize \
  --indir results/fase4_vuelo_plantacion \
  --out results/fase4_vuelo_plantacion/summary.csv \
  --config configs/conf_mayora.yaml
```

5. **Verificar KPIs de aplicación in-situ:**
   - Latencia P99 ≤ 50 ms → ✅/❌
   - PER (loss_pct) ≤ 1% → ✅/❌
   - Throughput UL ≥ 15 Mbps → ✅/❌

---

## Fase 5: Límites y Degradación (Edge Cases)

### Objetivo
Demostrar el comportamiento de la red cuando la señal cae (como en la simulación al inyectar ruido), confirmando el margen hasta perder el enlace de streaming HD.

### Procedimiento

1. **Test Degradado en Emplazamiento 2 (Edificio alejado):** Este sitio sirve para probar de forma natural una caída intencionada de potencia (-70 a -75 dBm).
2. **También**, camina hasta un borde de celda o pégate a la sombra de los edificios mientras corres el test para provocar que el SINR empeore y asimilar la simulación virtual.

3. Lanza la suite:
```bash
fiveg-measure run-suite \
  --config configs/conf_mayora.yaml \
  --outdir results/fase5_degradacion_emp2 \
  --tag "Fase5_Degradacion_$(date +%Y%m%d_%H%M)" \
  --start-server
```

4. Observa la caída en Throughput UL y el incremento de pérdida de paquetes o Latencia P99.

---

## Fase 6: Resumen Global y Dashboard

Al finalizar todas las pruebas de campo, generar un resumen global:

```bash
# Ver todos los resultados en el dashboard
fiveg-measure dashboard --indir results/ --port 8181
```

### Estructura esperada de resultados:

```
results/
├── fase3_emplazamiento1_optimo/
├── fase4_vuelo_plantacion/
└── fase5_degradacion_emp2/
```

---

## Checklist de Métricas Radio (rellenar en campo)

| Ubicación | RSRP (dBm) | RSRQ (dB) | SINR (dB) | Banda | Cell ID | Feko RSRP esperado |
|:---|:---|:---|:---|:---|:---|:---|
| Fase 3: Emplazamiento 1 idóneo | | | | | | -50 a -55 dBm |
| Fase 4: Vuelo Zona Verde inicio | | | | | | Variable |
| Fase 4: Vuelo Zona Verde fin | | | | | | Variable |
| Fase 5: Emplazamiento 2 alejado| | | | | | -70 a -75 dBm |
| Fase 5: Sombra intencionada | | | | | | Peor que -75 dBm |

---

## Checklist de KPIs R3 — Validación Final

| KPI | Objetivo | Fase 3 (Emp 1) | Fase 4 (Plantación) | Fase 5 (Degradado) |
|:---|:---|:---|:---|:---|
| Latencia E2E (P99) | ≤ 50 ms | | | |
| PER / Pérdida UDP | ≤ 1% | | | |
| Throughput TCP UL | ≥ 15 Mbps | | | |
| MEC Speed | ≤ 500 ms | | | |
| Reliability | ≥ 99% | | | |

---

## Notas Importantes

> [!WARNING]
> **Antes de cada run**, desactivar el Wi-Fi del portátil para asegurar que todo el tráfico pasa por la conexión 5G del router.

> [!TIP]
> Hacer **fotos de la pantalla del router** con las métricas de señal, además de documentar **las coordenadas exactas de medición**. Estas fotos cerrarán el bucle Feko ↔ Mundo real para el texto del R3.
