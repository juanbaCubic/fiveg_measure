# Proceso de Configuración y Solución de Problemas: fiveg_measure

Este documento detalla los pasos operativos y obstáculos encontrados (y resueltos) al configurar por primera vez el entorno de medición 5G utilizando un MacBook Pro (cliente) y un servidor remoto Linux (reflector de tráfico iperf3). 

Es útil como guía rápida de despliegue y solución de problemas cuando se vaya a usar el framework con **un nuevo Mac** o **un nuevo Servidor VPS**.

---

## 1. Conexión del Router 5G al Mac

**Objetivo:** Asegurar que todo el tráfico del framework pasa por el enlace Ethernet 100/1000 del router 5G (NETGEAR MR6150) y no por la red Wi-Fi local ni otras interfaces.

### Requisitos previos:
1. Conectar el router al Mac mediante un cable/adaptador USB-C a Ethernet.
2. **APAGAR EL WI-FI DEL MAC:** Fundamental para que el sistema operativo macOS fuerce el enrutamiento (`0.0.0.0/0`) por el adaptador Ethernet. (El Wi-Fi que emite el router se puede dejar encendido de cara a usar su App móvil).

### Obstáculo 1: El Mac reconoce el cable pero no hay Internet (Falta IPv4)
Al ejecutar `ifconfig`, la interfaz Ethernet (ej. `en5` o `en4`) aparecía con `status: active` y velocidad negociada, pero **solo obtenía una IP local IPv6** (`fe80::...`) y ninguna IPv4 (`inet 192.168...`). El comando `ping 8.8.8.8` daba *timeout*.

**Causa y Solución:**
1. **IP Passthrough en el Router:** Algunos routers móviles tienen este modo para pasar la IP pública directa a una máquina. Si no se negocia bien, bloquea la LAN local. Asegurarse de que en la administración del router el modo "IP Passthrough" está **desactivado** y el **Servidor DHCP está activado**.
2. **Bloqueo del Puerto del Mac:** macOS puede desactivar el puerto Ethernet silenciosamente por inactividad o un conflicto inicial de DHCP.
   - *Solución rápida:* Desenchufar y volver a enchufar el adaptador físico USB-C.
   - *Solución final:* **Reiniciar el router 5G** conectado al cable. Tras reiniciarlo, forzó la asignación DHCP, otorgando al Mac la IP `192.168.1.71`.

---

## 2. Configuración del Servidor Remoto (AWS/Ubuntu)

**Objetivo:** Configurar una máquina Linux en la nube para que actúe como "servidor reflector" recibiendo tráfico SSH, pings e iPerf3 desde el cliente Mac.

### Obstáculo 2: iPerf3 ausente y fallo de instalación remota (`paramiko`)
El comando `fiveg-measure doctor` o `remote-setup` indicó que `iperf3` no estaba instalado en el VPS. El intento de auto-isntalación nativa del framework (`sudo apt-get install -y iperf3` via SSH/paramiko) falló porque el usuario del VPS (`forge`) estaba configurado para **pedir contraseña de sudo** al abrir una sesión remota.

**Solución:** 
1. Conectarse manualmente vía SSH desde el Mac: 
   `ssh -i ~/.ssh/tu-llave.pem usuario@ip`
2. Instalar el programa preciso, **es vital instalar la versión `iperf3` y no la antigua `iperf`** (son incompatibles y solo la v3 emite salidas JSON que lee el script):
   `sudo apt-get update && sudo apt-get install -y iperf3`

### Obstáculo 3: Puerto 5201 de iPerf3 bloqueado (Timeout)
Al lanzar `fiveg-measure doctor`, la conexión SSH 22 daba OK `✓`, pero el puerto de iperf3 fallaba: `tcp:IP:5201,FAIL,timed out`. Un *timeout* implica que los paquetes de sonda caen en un firewall (cortafuegos).

**Causa y Solución (2 Capas de Firewall):**
1. **Firewall Perimetral del Proveedor de Nube (AWS Security Groups):**
   - El puerto 5201 no estaba expuesto al exterior. Se solucionó añadiendo una regla *Inbound* (De entrada) para **TCP/UDP, puerto 5201, origen `0.0.0.0/0` (Cualquier IPv4)**.
2. **Firewall Interno del Sistema Operativo Remoto (Ubuntu `ufw`):**
   - A pesar de abrir AWS, seguía fallando. Esto se debe a que la propia máquina Linux tenía un cortafuegos activo local (UFW) bloqueando el tráfico entrante no-SSH.
   - Se solucionó entrando por SSH al VPS y apagando o configurando *ufw*:
     `sudo ufw disable`

**Comprobación manual:**
Desde el Mac, sin usar Python, lanzar un netcat como test puro de conectividad:
`nc -zv IP_SERVIDOR 5201`
*(Si devuelve `succeeded!`, el canal está libre).*

---

## 3. Comprobación del Cliente Local (MacBook)

### Obstáculo 4: Herramientas faltantes localmente
El "Doctor" mostró fallos locales (`tool:iperf3` y `tool:mtr`).

**Solución:**
Instalar las dependencias de red en macOS utilizando Homebrew:
`brew install iperf3 mtr`

*Nota sobre MTR:* Incluso tras instalarlo, `mtr` dará fallo de doctor porque macOS requiere permisos de "root" (`sudo`) continuos para manejar paquetes de rastreo. Se pueden ignorar los avisos de MTR en el doctor si no se va a ejecutar con privilegios elevados, ya que el framework soporta un uso grácil ("graceful degradation") usando solo `ping` y `traceroute` puramente si MTR falla.

---

## ¿Cómo saber que estamos listos?
Antes de cada medición (o tras cambiar de VPS/Router):

1. **Wi-Fi Apagado en Mac.**
2. `ping 8.8.8.8` funciona fluido (Tenemos 5G real).
3. `my_config.yaml` apunta a la Interfaz Ethernet (ej. `en5`) y a la IP correcta del VPS con su llave SSH.
4. Lanza: `fiveg-measure doctor --config my_config.yaml`.
5. Si `tool:iperf3` y, críticamente, `tcp:IP_VPS:5201` dan **verde (OK)**, puedes iniciar el test sin miedo:
   `fiveg-measure run-suite --config my_config.yaml --outdir results/Test01 --tag "MyTest" --start-server`
