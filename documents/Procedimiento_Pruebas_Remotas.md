# Procedimiento de Pruebas: Escenario Remoto (Macro-Celda)

Este procedimiento describe cómo ejecutar el framework `fiveg_measure` cuando no estamos físicamente en La Mayora (Edge), sino conectados a través de la **Macro-celda / Torre Remota** utilizando la VPN.

---

## Paso 1: Verificación del Túnel de Red
Dado que el servidor (`10.34.1.31`) es una IP privada, la VPN es el único camino.

1.  **Conectar OpenVPN**: Asegúrate de que el icono está en verde y muestra "Securely Connected".
2.  **Prueba de "Heartbeat"**: Abre una terminal en tu Mac y lanza:
    ```bash
    ping -c 5 10.34.1.31
    ```
    *   **Si responde:** Pasa al Paso 2.
    *   **Si da Timeout:** Revisa la VPN o confirma que la máquina en La Mayora esté encendida.

---

## Paso 2: Preparación del Servidor (Remoto)
Antes de medir, debemos asegurar que el "cerebro" remoto tiene las herramientas listas.

1.  **Sincronización SSH:** Lanza el comando de configuración:
    ```bash
    fiveg-measure remote-setup --config configs/conf_mayora.yaml --install
    ```
    *   Este comando instalará `iperf3` y verificará el acceso con la contraseña configurada.

---

## Paso 3: Ejecución de la Suite (Macro-Cell)
Lanzaremos la medición completa. Es vital usar un `tag` descriptivo para el Report 3 (R3).

1.  **Lanzar Suite:**
    ```bash
    fiveg-measure run-suite --config configs/conf_mayora.yaml --outdir results/macro_cell_test --tag "MacroCell_Remote_V1" --start-server
    ```
    *   `--start-server`: Arrancará el servidor iPerf en La Mayora automáticamente antes de empezar los tests.

---

## Paso 4: Análisis de Resultados y KPIs
Una vez finalizada la suite, validamos si la torre remota cumple los mínimos de calidad del proyecto.

1.  **Generar Reporte de Validación:**
    ```bash
    fiveg-measure summarize --indir results/macro_cell_test --config configs/conf_mayora.yaml
    ```

2.  **Verificar KPIs Críticos:**
    *   **Latencia (P95) <= 50ms**: ¿La distancia a la torre afecta al control del dron?
    *   **PER <= 1%**: ¿Hay pérdida de paquetes por la lejanía de la macro-celda?
    *   **MEC Speed <= 500ms**: ¿El tiempo de respuesta del "cerebro" sigue siendo aceptable a través de esta ruta?

---

## Paso 5: Guardado de Evidencias
Copia el archivo `summary.csv` que se generará en la carpeta raíz para incluirlo en el próximo entregable formal.
