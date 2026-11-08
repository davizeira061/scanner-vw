"""
Servidor Web de Telemetria e Dashboard Automotivo para o Scanner-VW (OpenVAG).
Construído com bibliotecas nativas do Python (zero dependências externas),
permitindo acesso local (no PC) e remoto (via Wi-Fi/Hotspot no smartphone dentro do cofre do motor).
"""

import json
import time
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Optional
from core.kw1281 import KW1281Engine
from database.dtc_db import DTCDatabase
from database.telemetry import TelemetryLogger

SHARED_ENGINE: Optional[KW1281Engine] = None
SHARED_DTC_DB = DTCDatabase()
SHARED_LOGGER = TelemetryLogger()


HTML_PAGE = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>OpenVAG - Telemetria & Diagnóstico KKL</title>
    <style>
        :root {
            --bg: #0f172a;
            --card-bg: #1e293b;
            --accent: #38bdf8;
            --green: #22c55e;
            --red: #ef4444;
            --yellow: #f59e0b;
            --text: #f8fafc;
            --text-dim: #94a3b8;
            --border: #334155;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
        body { background-color: var(--bg); color: var(--text); padding: 16px; }
        header { display: flex; justify-content: space-between; align-items: center; padding-bottom: 16px; border-bottom: 1px solid var(--border); margin-bottom: 20px; }
        .logo { font-size: 1.5rem; font-weight: bold; color: var(--accent); display: flex; align-items: center; gap: 8px; }
        .badge { background: #065f46; color: #a7f3d0; padding: 4px 10px; border-radius: 9999px; font-size: 0.75rem; font-weight: bold; }
        .badge.sim { background: #78350f; color: #fde68a; }
        
        .grid-cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 16px; margin-bottom: 24px; }
        .card { background: var(--card-bg); border: 1px solid var(--border); border-radius: 12px; padding: 16px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.3); }
        .card-title { font-size: 0.85rem; color: var(--text-dim); text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 8px; }
        .card-value { font-size: 2.2rem; font-weight: bold; color: var(--text); display: flex; align-items: baseline; gap: 6px; }
        .card-unit { font-size: 1rem; color: var(--text-dim); }
        .card-bar { height: 6px; background: #334155; border-radius: 3px; margin-top: 12px; overflow: hidden; }
        .card-fill { height: 100%; width: 0%; background: var(--accent); transition: width 0.3s ease; }

        .chart-section { background: var(--card-bg); border: 1px solid var(--border); border-radius: 12px; padding: 16px; margin-bottom: 24px; }
        canvas { width: 100%; height: 180px; display: block; }

        .dtc-section { background: var(--card-bg); border: 1px solid var(--border); border-radius: 12px; padding: 16px; }
        .dtc-item { background: #0f172a; border-left: 4px solid var(--red); padding: 12px; border-radius: 6px; margin-top: 10px; }
        .btn { background: var(--accent); color: #0f172a; border: none; padding: 8px 16px; border-radius: 6px; font-weight: bold; cursor: pointer; }
        .btn.clear { background: var(--red); color: white; }
    </style>
</head>
<body>
    <header>
        <div class="logo">🚗 OpenVAG <span>Scanner</span></div>
        <div id="connBadge" class="badge">CONECTADO: 1AVP</div>
    </header>

    <div class="grid-cards">
        <div class="card">
            <div class="card-title">Rotação do Motor</div>
            <div class="card-value"><span id="valRpm">--</span><span class="card-unit">RPM</span></div>
            <div class="card-bar"><div id="barRpm" class="card-fill"></div></div>
        </div>
        <div class="card">
            <div class="card-title">Temperatura do Motor (ECT)</div>
            <div class="card-value"><span id="valTemp">--</span><span class="card-unit">°C</span></div>
            <div class="card-bar"><div id="barTemp" class="card-fill"></div></div>
        </div>
        <div class="card">
            <div class="card-title">Sonda Lambda</div>
            <div class="card-value"><span id="valLambda">--</span><span class="card-unit">V</span></div>
            <div class="card-bar"><div id="barLambda" class="card-fill"></div></div>
        </div>
        <div class="card">
            <div class="card-title">Pressão Coletor (MAP)</div>
            <div class="card-value"><span id="valMap">--</span><span class="card-unit">mbar</span></div>
            <div class="card-bar"><div id="barMap" class="card-fill"></div></div>
        </div>
        <div class="card">
            <div class="card-title">Tensão da Bateria</div>
            <div class="card-value"><span id="valBat">--</span><span class="card-unit">V</span></div>
            <div class="card-bar"><div id="barBat" class="card-fill"></div></div>
        </div>
        <div class="card">
            <div class="card-title">Avanço de Ignição</div>
            <div class="card-value"><span id="valTiming">--</span><span class="card-unit">° APMS</span></div>
            <div class="card-bar"><div id="barTiming" class="card-fill"></div></div>
        </div>
    </div>

    <div class="chart-section">
        <div class="card-title">Osciloscópio de Telemetria ao Vivo (RPM & Sonda)</div>
        <canvas id="scopeCanvas" width="800" height="200"></canvas>
    </div>

    <div class="dtc-section">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <div class="card-title">Diagnóstico de Falhas (DTCs da ECU)</div>
            <button class="btn clear" onclick="clearDTCs()">Limpar Memória de Avarias</button>
        </div>
        <div id="dtcList">
            <p style="color: var(--text-dim); margin-top: 8px;">Nenhuma falha gravada.</p>
        </div>
    </div>

    <script>
        const canvas = document.getElementById("scopeCanvas");
        const ctx = canvas.getContext("2d");
        const rpmHistory = [];
        const maxPoints = 80;

        function updateTelemetry() {
            fetch('/api/telemetry')
                .then(r => r.json())
                .then(data => {
                    if (data.fields) {
                        data.fields.forEach(f => {
                            if (f.name.includes("Rotação") || f.unit === "RPM") {
                                document.getElementById("valRpm").innerText = f.value;
                                document.getElementById("barRpm").style.width = Math.min(100, (f.value / 6500) * 100) + "%";
                                rpmHistory.push(f.value);
                                if (rpmHistory.length > maxPoints) rpmHistory.shift();
                            }
                            if (f.name.includes("Temp") || f.unit === "°C") {
                                document.getElementById("valTemp").innerText = f.value;
                                document.getElementById("barTemp").style.width = Math.min(100, (f.value / 120) * 100) + "%";
                            }
                            if (f.name.includes("Lambda") || (f.unit === "V" && f.value < 2.0)) {
                                document.getElementById("valLambda").innerText = f.value;
                                document.getElementById("barLambda").style.width = Math.min(100, (f.value / 1.0) * 100) + "%";
                            }
                            if (f.name.includes("MAP") || f.unit === "mbar") {
                                document.getElementById("valMap").innerText = f.value;
                                document.getElementById("barMap").style.width = Math.min(100, (f.value / 1050) * 100) + "%";
                            }
                            if (f.name.includes("Bateria") || (f.unit === "V" && f.value > 8.0)) {
                                document.getElementById("valBat").innerText = f.value;
                                document.getElementById("barBat").style.width = Math.min(100, ((f.value - 10) / 5) * 100) + "%";
                            }
                            if (f.name.includes("Ponto") || f.unit.includes("APMS")) {
                                document.getElementById("valTiming").innerText = f.value;
                                document.getElementById("barTiming").style.width = Math.min(100, (f.value / 40) * 100) + "%";
                            }
                        });
                        drawScope();
                    }
                }).catch(() => {});
        }

        function drawScope() {
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            // Grade
            ctx.strokeStyle = "#334155";
            ctx.lineWidth = 1;
            ctx.beginPath();
            for(let y = 0; y < canvas.height; y += 40) { ctx.moveTo(0, y); ctx.lineTo(canvas.width, y); }
            ctx.stroke();

            if (rpmHistory.length < 2) return;
            ctx.strokeStyle = "#38bdf8";
            ctx.lineWidth = 2.5;
            ctx.beginPath();
            const step = canvas.width / (maxPoints - 1);
            rpmHistory.forEach((rpm, idx) => {
                // Escala 0 a 4000 RPM
                const norm = 1 - (rpm / 4000);
                const y = norm * canvas.height;
                const x = idx * step;
                if (idx === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
            });
            ctx.stroke();
        }

        function fetchDTCs() {
            fetch('/api/dtcs')
                .then(r => r.json())
                .then(data => {
                    const container = document.getElementById("dtcList");
                    if (!data.dtcs || data.dtcs.length === 0) {
                        container.innerHTML = '<p style="color: #22c55e; margin-top: 8px;">✓ Nenhuma falha gravada na ECU.</p>';
                        return;
                    }
                    let html = '';
                    data.dtcs.forEach(d => {
                        html += `<div class="dtc-item">
                            <h4 style="color: #ef4444;">Código VAG: ${d.code} (${d.info.obd_code || 'P----'})</h4>
                            <p style="font-weight: bold; margin-top: 4px;">${d.info.component}</p>
                            <p style="color: var(--text-dim); font-size: 0.9rem; margin-top: 4px;">${d.info.description}</p>
                            <p style="color: #f59e0b; font-size: 0.85rem; margin-top: 6px;"><b>Ação Mecânica:</b> ${d.info.mechanical_fix}</p>
                        </div>`;
                    });
                    container.innerHTML = html;
                });
        }

        function clearDTCs() {
            fetch('/api/clear_dtcs', { method: 'POST' })
                .then(() => fetchDTCs());
        }

        setInterval(updateTelemetry, 400);
        setInterval(fetchDTCs, 5000);
        fetchDTCs();
    </script>
</body>
</html>
"""


class WebTelemetryHandler(BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        pass  # Silencia logs de requisição no console

    def do_GET(self):
        global SHARED_ENGINE, SHARED_DTC_DB, SHARED_LOGGER

        if self.path == "/" or self.path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_PAGE.encode("utf-8"))

        elif self.path == "/api/telemetry":
            fields = []
            if SHARED_ENGINE and SHARED_ENGINE.connected:
                fields = SHARED_ENGINE.read_measuring_group(1)
                SHARED_LOGGER.log_measuring_fields(1, fields)

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"fields": fields}).encode("utf-8"))

        elif self.path == "/api/dtcs":
            dtcs_list = []
            if SHARED_ENGINE and SHARED_ENGINE.connected:
                raw_dtcs = SHARED_ENGINE.read_dtcs()
                for item in raw_dtcs:
                    code = item["code"]
                    info = SHARED_DTC_DB.lookup(code)
                    dtcs_list.append({"code": code, "info": info})

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"dtcs": dtcs_list}).encode("utf-8"))

        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        global SHARED_ENGINE
        if self.path == "/api/clear_dtcs":
            if SHARED_ENGINE and SHARED_ENGINE.connected:
                SHARED_ENGINE.clear_dtcs()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok"}).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()


def start_web_server(engine: KW1281Engine, port: int = 8080):
    global SHARED_ENGINE
    SHARED_ENGINE = engine
    server = HTTPServer(("0.0.0.0", port), WebTelemetryHandler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    return server
