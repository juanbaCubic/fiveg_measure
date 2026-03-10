# Plan de Validación: Estudio de Cobertura Altair Feko (La Mayora)

Este documento resume el plan de validación técnica del estudio teórico de cobertura realizado con **Altair Feko**, integrando el uso del framework `fiveg_measure` como herramienta principal de verificación de KPIs.

---

## 1. Objetivo del Análisis Teórico
El estudio realizado en el **Report 2 (R2)** utiliza simulaciones electromagnéticas para crear un "gemelo digital" de la red en La Mayora. Se basa en:
*   Parámetros de antenas (altura, ganancia, potencia).
*   Ubicación de emplazamientos (Site 1 y Site 2).
*   Modelos de propagación del terreno.

## 2. Acciones de Validación Real (Campo)

Para cerrar el bucle entre la simulación y la realidad, se ejecutarán las siguientes tres fases:

### Fase A: Escaneo de RF (Nemo Handy)
*   **Herramienta:** Escáner Nemo Handy.
*   **Métricas:** RSRP (Potencia), RSRQ (Calidad) y SINR (Ruido).
*   **Propósito:** Calibrar el modelo de propagación electromagnética de FEKO con datos reales de la señal de radio.

### Fase B: Verificación de KPIs (fiveg_measure)
El framework `fiveg_measure` validará la "capa de servicio" sobre la cobertura de radio:
*   **Latencia Extremo a Extremo (E2E):** Validar que la latencia se mantiene estable para el control del dron (medido vía `ping` y `tcp_connect`).
*   **Packet Error Rate (PER):** La meta es **PER ≤ 1%**. Validado mediante los tests de pérdida de paquetes UDP (`iperf_udp`).
*   **Throughput de Vídeo:** Asegurar el caudal de subida (Uplink) necesario para streaming HD desde el dron (medido vía `iperf_tcp --reverse`).

### Fase C: Monitorización de Carga (Bufferbloat)
*   Verificar que la latencia no se degrada críticamente cuando el dron envía ráfagas de datos de alta resolución (medido vía `bufferbloat_test`).

---

## 3. Puntos Críticos de Medición y Trayectorias

La validación debe centrarse en los puntos definidos en el mapa del proyecto:

1.  **Site 1 (Micro-celda - Water Tank):** Crítico para la zona de cultivos. Se debe medir la estabilidad del Uplink de vídeo en las cercanías del mástil.
2.  **Site 2 (Macro-celda - Torre Remota):** Proporciona la cobertura de área amplia. Crítico para validar el traspaso (handover) y la cobertura en los límites de la plantación.
3.  **Líneas de Cultivo (Crop Rows):** Las trayectorias de los drones deben ser el eje de las mediciones de `fiveg_measure` para asegurar una navegación autónoma segura.

---

## 4. Notas de Implementación con fiveg_measure

Para una correlación perfecta con el estudio de Feko:
*   **Captura de Señal:** Si el router MR6150 permite el acceso a su API, `fiveg_measure` capturará RSRP/SINR automáticamente. De lo contrario, se deben rellenar en el campo `router_manual:` del archivo `configs/conf_mayora.yaml` tras cada vuelo.
*   **Tagging:** Utilizar el parámetro `--tag` para identificar la trayectoria o el "Site" medido (ej: `--tag "Site1_Row5_Flight1"`).
