# Guía de Configuración SIM: La Mayora

Esta guía detalla los pasos para configurar la tarjeta SIM de La Mayora en el router **NETGEAR Nighthawk M6 Pro (MR6150)**.

---

## 1. Datos de la SIM (Aprovisionamiento)
Según las instrucciones del técnico (Javier):
*   **APN:** `internet1`
*   **PIN:** No tiene (desactivado).
*   **Factor de forma:** La SIM viene con los tres recortes estándar (Mini, Micro, Nano). Asegúrate de usar el tamaño que encaja en la ranura del MR6150.

---

## 2. Configuración del Router (Paso a Paso)

1.  **Conexión:** Conéctate al router vía cable Ethernet o mediante su Wi-Fi (`192.168.1.1`).
2.  **Acceso Web:** Abre un navegador y entra en [http://192.168.1.1](http://192.168.1.1).
3.  **Login:** Introduce tu contraseña de administrador.
4.  **Menú APN:**
    *   Ve a **Configuración (Settings)** > **Red (Network)** > **APN**.
    *   Haz clic en **Añadir (Add)**.
5.  **Nuevo Perfil:**
    *   **Nombre del Perfil:** `Mayora`
    *   **APN:** `internet1`
    *   **Autenticación:** `None` / `Ninguna`.
    *   **Usuario/Contraseña:** Vacíos.
6.  **Guardar y Activar:** Haz clic en **Guardar (Save)** y luego selecciona el perfil "Mayora" como **Predeterminado (Default)**.

---

## 3. Verificación

Sabrás que la configuración es correcta si:
*   En la pantalla del router aparece el icono **5G** o **LTE** con barras de señal.
*   En el panel web, el estado de la conexión indica **"Connected"**.
*   Puedes navegar por internet o hacer ping a la IP del servidor de destino (`10.34.1.31`).

---

## 4. Nota sobre VPN

Al utilizar esta SIM específica, el router ya se encuentra dentro de la red privada del operador/cliente. 
*   **IMPORTANTE:** Es muy probable que **NO necesites activar la VPN de OpenVPN** del Mac para llegar a la IP `10.34.1.31`, ya que el propio router te dará una dirección IP interna capaz de ver ese servidor directamente.
*   Si el test falla sin VPN, prueba a activarla, pero la ruta óptima para latencia será siempre sin el túnel si la red lo permite.

---

## 5. Solución de Problemas
*   **SIM Locked:** Si el router pide un código, revisa si hay algún PIN por defecto (aunque se haya dicho que no tiene).
*   **No Data:** Verifica que el APN está escrito exactamente como `internet1` (sin espacios ni mayúsculas).
