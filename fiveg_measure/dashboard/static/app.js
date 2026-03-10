/**
 * fiveg_measure Dashboard — app.js
 * Loads CSV data via REST API and renders:
 *   • Time series charts (Chart.js) per metric group
 *   • System metrics charts (CPU, memory, network)
 *   • Geolocation map (Leaflet.js)
 *   • Sidebar KPI cards & router signal panel
 */

// ── API helpers ──────────────────────────────────────────────────────────────

const api = {
    async get(path) {
        const r = await fetch(path);
        if (!r.ok) throw new Error(`HTTP ${r.status}: ${path}`);
        return r.json();
    },
    runs: () => api.get('/api/runs'),
    metrics: (runId) => api.get(`/api/metrics?run_id=${encodeURIComponent(runId)}`),
    system: (runId) => api.get(`/api/system?run_id=${encodeURIComponent(runId)}`),
    metadata: (runId) => api.get(`/api/metadata?run_id=${encodeURIComponent(runId)}`),
    location: (runId) => api.get(`/api/location?run_id=${encodeURIComponent(runId)}`),
};

// ── State ────────────────────────────────────────────────────────────────────

let currentRunId = null;
let chartInstances = {};
let map = null;
let markerLayer = null;

// ── Chart.js default config ──────────────────────────────────────────────────

Chart.defaults.color = '#718096';
Chart.defaults.borderColor = 'rgba(255,255,255,0.06)';
Chart.defaults.font.family = "'Inter', system-ui, sans-serif";
Chart.defaults.font.size = 11;

const PALETTE = [
    '#63b3ed', '#9f7aea', '#68d391', '#fc8181', '#fbd38d',
    '#76e4f7', '#f687b3', '#b794f4', '#9ae6b4', '#feb2b2',
];

function chartDefaults(label, color = PALETTE[0]) {
    return {
        label,
        borderColor: color,
        backgroundColor: color + '1a',
        borderWidth: 1.8,
        pointRadius: 2,
        pointHoverRadius: 5,
        tension: 0.35,
        fill: true,
    };
}

function makeTimeAxis(labels) {
    return {
        type: 'category',
        ticks: {
            maxTicksLimit: 8,
            maxRotation: 30,
            callback: (val, idx) => {
                const t = labels[idx];
                if (!t) return '';
                try {
                    const d = new Date(t);
                    return `${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}:${d.getSeconds().toString().padStart(2, '0')}`;
                } catch { return t; }
            }
        }
    };
}

function createOrUpdateChart(canvasId, type, data, options = {}) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;
    if (chartInstances[canvasId]) {
        chartInstances[canvasId].destroy();
    }
    chartInstances[canvasId] = new Chart(canvas.getContext('2d'), {
        type,
        data,
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { mode: 'index', intersect: false },
            plugins: {
                legend: {
                    position: 'top',
                    labels: { boxWidth: 12, padding: 12, usePointStyle: true },
                },
                tooltip: {
                    backgroundColor: 'rgba(10,14,25,0.95)',
                    borderColor: 'rgba(99,179,237,0.3)',
                    borderWidth: 1,
                    padding: 10,
                    cornerRadius: 8,
                    callbacks: {
                        title: (items) => {
                            const t = items[0]?.label;
                            if (!t) return '';
                            try {
                                return new Date(t).toLocaleString('es-ES');
                            } catch { return t; }
                        }
                    }
                },
            },
            scales: {
                x: { grid: { color: 'rgba(255,255,255,0.04)' } },
                y: { grid: { color: 'rgba(255,255,255,0.04)' } },
            },
            animation: { duration: 500, easing: 'easeOutQuart' },
            ...options,
        }
    });
}

// ── Group metrics by name ────────────────────────────────────────────────────

function groupMetrics(rows) {
    // rows from measurements_long.csv
    const groups = {};
    for (const r of rows) {
        const key = r.metric_name;
        if (!groups[key]) groups[key] = [];
        groups[key].push(r);
    }
    return groups;
}

// Gather unique combinations of (metric_name, direction) per test_name
function buildSeriesMap(rows) {
    // Returns: { category -> { seriesKey -> [{timestamp, metric_value, test_name, direction, iteration, notes}] } }
    const CATEGORY_MAP = {
        rtt_ms: 'latency', connect_time_ms: 'latency',
        rtt_avg_ms: 'latency', rtt_p50_ms: 'latency',
        rtt_idle_p50: 'bufferbloat', rtt_load_p50: 'bufferbloat',
        rtt_increase_ms: 'bufferbloat', rtt_load_p95: 'bufferbloat',
        loss_pct: 'loss', mtr_loss_pct: 'loss',
        jitter_ms: 'jitter',
        throughput_mbps: 'throughput',
        mtr_avg_ms: 'latency', hop_avg_rtt_ms: 'latency',
        cpu_percent: 'system', mem_used_mb: 'system',
    };

    const cats = {};
    for (const r of rows) {
        const cat = CATEGORY_MAP[r.metric_name] || 'other';
        if (!cats[cat]) cats[cat] = {};
        const key = `${r.test_name}:${r.metric_name}:${r.direction || 'NA'}`;
        if (!cats[cat][key]) cats[cat][key] = [];
        cats[cat][key].push(r);
    }
    return cats;
}

function renderCategoryChart(canvasId, seriesMap, unit = '', yLabel = '') {
    const series = Object.entries(seriesMap);
    if (!series.length) return;

    // Collect all timestamps and sort
    const allTs = [...new Set(series.flatMap(([, pts]) => pts.map(p => p.timestamp || '')))].sort();

    const datasets = series.map(([key, pts], i) => {
        const label = key.split(':').slice(0, 2).join(' › ');
        const valMap = {};
        for (const p of pts) valMap[p.timestamp] = parseFloat(p.metric_value);
        return {
            ...chartDefaults(label, PALETTE[i % PALETTE.length]),
            data: allTs.map(ts => valMap[ts] ?? null),
            spanGaps: true,
        };
    });

    createOrUpdateChart(canvasId, 'line', {
        labels: allTs,
        datasets,
    }, {
        scales: {
            x: makeTimeAxis(allTs),
            y: {
                title: { display: !!yLabel, text: yLabel || unit },
                grid: { color: 'rgba(255,255,255,0.04)' },
            }
        }
    });
}

// ── System metrics chart ─────────────────────────────────────────────────────

function renderSystemMetrics(rows) {
    if (!rows.length) return;

    const timestamps = rows.map(r => r.timestamp);
    const cpu = rows.map(r => parseFloat(r.cpu_percent));
    const mem = rows.map(r => parseFloat(r.mem_used_mb));

    createOrUpdateChart('chart-cpu', 'line', {
        labels: timestamps,
        datasets: [
            { ...chartDefaults('CPU %', PALETTE[0]), data: cpu, fill: true },
        ]
    }, {
        scales: {
            x: makeTimeAxis(timestamps),
            y: { min: 0, max: 100, title: { display: true, text: '%' }, grid: { color: 'rgba(255,255,255,0.04)' } }
        }
    });

    createOrUpdateChart('chart-mem', 'line', {
        labels: timestamps,
        datasets: [
            { ...chartDefaults('Memory MB', PALETTE[1]), data: mem, fill: true },
        ]
    }, {
        scales: {
            x: makeTimeAxis(timestamps),
            y: { title: { display: true, text: 'MB' }, grid: { color: 'rgba(255,255,255,0.04)' } }
        }
    });

    // Network throughput (derivative of bytes)
    const bytesRecv = rows.map(r => parseInt(r.net_bytes_recv) || 0);
    const bytesSent = rows.map(r => parseInt(r.net_bytes_sent) || 0);
    const rxMbps = [null], txMbps = [null];
    for (let i = 1; i < rows.length; i++) {
        const dt = 1; // 1-second sampling
        rxMbps.push(((bytesRecv[i] - bytesRecv[i - 1]) * 8 / 1e6 / dt).toFixed(3));
        txMbps.push(((bytesSent[i] - bytesSent[i - 1]) * 8 / 1e6 / dt).toFixed(3));
    }

    createOrUpdateChart('chart-net', 'line', {
        labels: timestamps,
        datasets: [
            { ...chartDefaults('RX Mbps', PALETTE[2]), data: rxMbps, fill: true },
            { ...chartDefaults('TX Mbps', PALETTE[3]), data: txMbps, fill: true },
        ]
    }, {
        scales: {
            x: makeTimeAxis(timestamps),
            y: { title: { display: true, text: 'Mbps' }, min: 0, grid: { color: 'rgba(255,255,255,0.04)' } }
        }
    });
}

// ── KPI calculation ──────────────────────────────────────────────────────────

function calcKPIs(rows) {
    const vals = (name) => rows
        .filter(r => r.metric_name === name)
        .map(r => parseFloat(r.metric_value))
        .filter(v => !isNaN(v));

    const p50 = (arr) => {
        if (!arr.length) return null;
        const s = [...arr].sort((a, b) => a - b);
        return s[Math.floor(s.length * 0.5)] ?? null;
    };
    const avg = (arr) => arr.length ? arr.reduce((a, b) => a + b, 0) / arr.length : null;

    return {
        rtt_p50: p50(vals('rtt_ms'))?.toFixed(1),
        rtt_avg: avg(vals('rtt_ms'))?.toFixed(1),
        loss_pct: avg(vals('loss_pct'))?.toFixed(2),
        jitter_p50: p50(vals('jitter_ms'))?.toFixed(2),
        dl_mbps: p50(vals('throughput_mbps')?.filter ? vals('throughput_mbps') : [])?.toFixed(1),
        bb_increase: avg(vals('rtt_increase_ms'))?.toFixed(1),
        connect_ms: avg(vals('connect_time_ms'))?.toFixed(1),
    };
}

function setKPI(id, value, suffix = '') {
    const el = document.getElementById(id);
    if (el) el.textContent = (value != null && value !== undefined) ? `${value}${suffix}` : '—';
}

// ── Sidebar metadata ─────────────────────────────────────────────────────────

function renderSidebar(meta, kpis) {
    setKPI('kpi-rtt', kpis.rtt_p50, '');
    setKPI('kpi-loss', kpis.loss_pct, '');
    setKPI('kpi-jitter', kpis.jitter_p50, '');
    setKPI('kpi-dl', kpis.dl_mbps, '');
    setKPI('kpi-bb', kpis.bb_increase, '');
    setKPI('kpi-conn', kpis.connect_ms, '');

    // Router badge
    document.getElementById('router-tech').textContent = meta.router_tech || '—';
    document.getElementById('router-rsrp').textContent = meta.router_rsrp ? `${meta.router_rsrp} dBm` : '—';
    document.getElementById('router-rsrq').textContent = meta.router_rsrq ? `${meta.router_rsrq} dB` : '—';
    document.getElementById('router-sinr').textContent = meta.router_sinr ? `${meta.router_sinr} dB` : '—';
    document.getElementById('router-band').textContent = meta.router_band || '—';

    // Run info
    document.getElementById('meta-iface').textContent = meta.interface_name || '—';
    document.getElementById('meta-ip').textContent = meta.interface_ip || '—';
    document.getElementById('meta-pubip').textContent = meta.public_ip || '—';
    document.getElementById('meta-server').textContent = meta.server_host || '—';
    document.getElementById('meta-wifi').textContent = meta.wifi_active === 'True' ? '⚠ Activo' : '✓ Off';
    document.getElementById('meta-model').textContent = meta.mac_model || '—';

    const tsEl = document.getElementById('meta-ts');
    if (tsEl && meta.timestamp_start) {
        try {
            tsEl.textContent = new Date(meta.timestamp_start).toLocaleString('es-ES');
        } catch { tsEl.textContent = meta.timestamp_start; }
    }
}

// ── Map ──────────────────────────────────────────────────────────────────────

function initMap() {
    if (map) return;
    map = L.map('map', { zoomControl: true, attributionControl: true }).setView([40.416, -3.703], 4);
    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a> &copy; <a href="https://carto.com/">CARTO</a>',
        subdomains: 'abcd', maxZoom: 19,
    }).addTo(map);
    markerLayer = L.layerGroup().addTo(map);
}

function renderMap(locData, meta, kpis) {
    initMap();
    markerLayer.clearLayers();

    if (!locData || !locData.lat) return;

    const { lat, lon, city, country, isp, org, query } = locData;

    const pulseIcon = L.divIcon({
        className: '',
        html: `
      <div style="position:relative;width:32px;height:32px;">
        <div style="position:absolute;inset:0;background:rgba(99,179,237,0.2);border-radius:50%;animation:pulse 2s infinite;"></div>
        <div style="position:absolute;inset:6px;background:#63b3ed;border-radius:50%;border:2px solid #fff;"></div>
      </div>`,
        iconSize: [32, 32],
        iconAnchor: [16, 16],
    });

    const popupHtml = `
    <div style="min-width:200px;line-height:1.7">
      <div style="font-weight:700;font-size:14px;margin-bottom:8px;color:#63b3ed">📍 ${city || ''}, ${country || ''}</div>
      <div><span style="color:#718096">IP Pública:</span> <b>${query || meta.public_ip || '—'}</b></div>
      <div><span style="color:#718096">ISP:</span> ${isp || org || '—'}</div>
      <hr style="border-color:rgba(255,255,255,0.08);margin:8px 0">
      <div><span style="color:#718096">RTT p50:</span> <b>${kpis.rtt_p50 ?? '—'} ms</b></div>
      <div><span style="color:#718096">Jitter p50:</span> <b>${kpis.jitter_p50 ?? '—'} ms</b></div>
      <div><span style="color:#718096">Loss:</span> <b>${kpis.loss_pct ?? '—'} %</b></div>
      <div><span style="color:#718096">DL:</span> <b>${kpis.dl_mbps ?? '—'} Mbps</b></div>
      <hr style="border-color:rgba(255,255,255,0.08);margin:8px 0">
      <div><span style="color:#718096">Interfaz:</span> ${meta.interface_name || '—'} — ${meta.interface_ip || '—'}</div>
      <div><span style="color:#718096">Servidor:</span> ${meta.server_host || '—'}</div>
      <div><span style="color:#718096">Router:</span> ${meta.router_tech || '—'} ${meta.router_band ? '/ ' + meta.router_band : ''}</div>
    </div>`;

    const marker = L.marker([lat, lon], { icon: pulseIcon })
        .addTo(markerLayer)
        .bindPopup(popupHtml, { maxWidth: 300 })
        .openPopup();

    map.setView([lat, lon], 10, { animate: true });
    setTimeout(() => map.invalidateSize(), 200);
}

// ── Main load ────────────────────────────────────────────────────────────────

async function loadDashboard(runId) {
    currentRunId = runId;
    setStatus('Cargando datos...', false);

    try {
        const [metrics, sysMetrics, meta, locData] = await Promise.all([
            api.metrics(runId),
            api.system(runId),
            api.metadata(runId),
            api.location(runId).catch(() => null),
        ]);

        // KPIs
        const kpis = calcKPIs(metrics);
        renderSidebar(meta, kpis);

        // Time series charts
        const catMap = buildSeriesMap(metrics);

        // Latency tab
        renderCategoryChart('chart-latency', catMap['latency'] || {}, 'ms', 'Latencia (ms)');
        renderCategoryChart('chart-loss', catMap['loss'] || {}, '%', 'Pérdida (%)');
        renderCategoryChart('chart-jitter', catMap['jitter'] || {}, 'ms', 'Jitter (ms)');
        renderCategoryChart('chart-throughput', catMap['throughput'] || {}, 'Mbps', 'Throughput (Mbps)');
        renderCategoryChart('chart-bufferbloat', catMap['bufferbloat'] || {}, 'ms', 'RTT (ms)');
        renderCategoryChart('chart-other', catMap['other'] || {}, '', 'Otras métricas');

        // System tab
        if (sysMetrics.length) renderSystemMetrics(sysMetrics);

        // Map tab
        renderMap(locData, meta, kpis);

        setStatus(`${metrics.length} métricas cargadas — ${new Date().toLocaleTimeString('es-ES')}`, false);
    } catch (err) {
        console.error(err);
        setStatus(`Error: ${err.message}`, true);
    }
}

// ── Run selector ─────────────────────────────────────────────────────────────

async function loadRuns() {
    const sel = document.getElementById('run-select');
    try {
        const runs = await api.runs();
        sel.innerHTML = '';
        if (!runs.length) {
            sel.innerHTML = '<option value="">— Sin datos aún —</option>';
            setStatus('No se encontraron runs. Ejecuta fiveg-measure run-suite primero.', true);
            return;
        }
        for (const r of runs) {
            const label = `${r.tag || r.run_id.slice(0, 8)} — ${r.timestamp_start?.slice(0, 19) || '?'}`;
            const opt = document.createElement('option');
            opt.value = r.run_id;
            opt.textContent = label;
            sel.appendChild(opt);
        }
        // Auto-select most recent
        const firstRunId = runs[0].run_id;
        sel.value = firstRunId;
        loadDashboard(firstRunId);
    } catch (err) {
        setStatus(`No se pudo conectar con el servidor: ${err.message}`, true);
    }
}

// ── Tab switching ─────────────────────────────────────────────────────────────

function initTabs() {
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
            btn.classList.add('active');
            const panel = document.getElementById('panel-' + btn.dataset.tab);
            if (panel) {
                panel.classList.add('active');
                // Invalidate map size on tab switch
                if (btn.dataset.tab === 'map' && map) {
                    setTimeout(() => map.invalidateSize(), 100);
                }
                // Resize charts on switch
                Object.values(chartInstances).forEach(c => c.resize());
            }
        });
    });
}

// ── Status bar ───────────────────────────────────────────────────────────────

function setStatus(msg, isError) {
    const dot = document.querySelector('#status-bar .dot');
    const txt = document.getElementById('status-text');
    if (dot) dot.className = 'dot' + (isError ? ' error' : '');
    if (txt) txt.textContent = msg;
}

// ── Init ─────────────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
    initTabs();
    try {
        initMap();
    } catch (err) {
        console.warn('Leaflet map could not be initialized:', err);
    }
    loadRuns();

    document.getElementById('run-select').addEventListener('change', (e) => {
        if (e.target.value) loadDashboard(e.target.value);
    });

    document.getElementById('refresh-btn').addEventListener('click', () => {
        if (currentRunId) loadDashboard(currentRunId);
        else loadRuns();
    });
});
