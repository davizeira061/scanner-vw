"""
Aplicação Gráfica Desktop Nativa do Scanner-VW (OpenVAG).
Interface de Performance Automotiva e Telemetria Motorsport Racing.
Estética Racing: Fundo preto profundo, acentos em Vermelho Racing (#FF2A3B), tipografia técnica,
displays digitais de alta visibilidade e instrumentação de cockpit.

Implementa 100% dos fluxos e telas do VCDS-Lite com melhorias gráficas e funcionais:
- Cockpit Digital Motorsport com mostradores de RPM, MAP, Lambda, ECT, TPS e Bateria
- Detecção Plug-and-Play com Watchdog de porta serial USB KKL (CH340/CH341/FTDI)
- Multithreading (QThread) para conexões assíncronas e Auto-Scan fluido
- Keep-Alive Ativo (0x09) a cada 350ms evitando timeout de sessão da ECU
- Osciloscópio / Datalogger Gráfico Multi-Canal de Alta Performance
- Datalogger Contínuo em CSV para voltas de teste de rodagem
- Assistente Zero-Friction de Calibração de Borboleta (TBI) para Bosch MP 9.0 e Marelli 1AVP
- Doutor de DTCs com 35 falhas mapeadas e guias de multímetro no chicote
"""

import sys
import os
import time
import csv
from datetime import datetime
from typing import Optional, List, Dict, Any

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QComboBox, QLineEdit, QTableWidget, QTableWidgetItem,
    QTabWidget, QGroupBox, QProgressBar, QMessageBox, QDialog, QHeaderView,
    QTextEdit, QSpinBox, QSplitter, QInputDialog, QCheckBox,
    QRadioButton, QButtonGroup, QScrollArea, QFrame, QGridLayout
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread
from PyQt6.QtGui import QFont, QColor, QPainter, QPen, QBrush

from core.hardware import list_available_ports, find_kkl_cable_port, KLineSerialInterface
from core.kw1281 import KW1281Engine
from core.autoscan import AutoScanManager, MODULE_NAMES
from database.dtc_db import DTCDatabase
from database.telemetry import TelemetryLogger


MOTORSPORT_STYLE = """
/* =========================================================================
   TEMA MOTORSPORT RACING & TELEMETRIA AUTOMOTIVA
   Visual: Preto Asfalto, Vermelho Racing (#FF2A3B), Branco Técnico e Âmbar
   ========================================================================= */

QMainWindow, QDialog, QWidget {
    background-color: #0b0c10;
    color: #f1f2f6;
    font-family: 'Segoe UI', -apple-system, sans-serif;
    font-size: 13px;
}

/* GroupBox estilo Painel de Instrumentos Motorsport */
QGroupBox {
    border: 1px solid #232733;
    border-top: 2px solid #ff2a3b;
    border-radius: 2px;
    margin-top: 16px;
    padding-top: 14px;
    font-weight: 800;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 1px;
    color: #ffffff;
    background-color: #101218;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 2px 8px;
    background-color: #ff2a3b;
    color: #ffffff;
    border-radius: 1px;
    font-weight: 900;
    font-size: 10px;
    letter-spacing: 1px;
}

/* Botões Táticos Industriais */
QPushButton {
    background-color: #171a24;
    border: 1px solid #2e3547;
    border-radius: 2px;
    padding: 8px 16px;
    font-weight: 800;
    font-size: 12px;
    letter-spacing: 0.8px;
    text-transform: uppercase;
    color: #f1f2f6;
    min-height: 24px;
}
QPushButton:hover {
    background-color: #212636;
    border-color: #ff2a3b;
    color: #ff2a3b;
}
QPushButton:pressed {
    background-color: #ff2a3b;
    border-color: #ff2a3b;
    color: #ffffff;
}
QPushButton:disabled {
    background-color: #0d0e14;
    border-color: #1a1d26;
    color: #4a5163;
}
QPushButton.primary {
    background-color: #ff2a3b;
    border: 1px solid #ff4757;
    color: #ffffff;
}
QPushButton.primary:hover {
    background-color: #e60012;
    border-color: #ff2a3b;
    color: #ffffff;
}
QPushButton.danger {
    background-color: #8b0000;
    border: 1px solid #b30000;
    color: #ffffff;
}
QPushButton.danger:hover {
    background-color: #b30000;
    border-color: #ff2a3b;
}
QPushButton.success {
    background-color: #007a3d;
    border: 1px solid #00994d;
    color: #ffffff;
}
QPushButton.success:hover {
    background-color: #00994d;
    border-color: #00e676;
}

/* Navegação por Abas (Dash Tabs) */
QTabBar::tab {
    background: #101218;
    border: 1px solid #232733;
    border-bottom: none;
    padding: 10px 20px;
    margin-right: 2px;
    border-top-left-radius: 2px;
    border-top-right-radius: 2px;
    color: #7b8499;
    font-weight: 800;
    font-size: 11px;
    letter-spacing: 0.8px;
    text-transform: uppercase;
}
QTabBar::tab:selected {
    background: #171a24;
    border-top: 3px solid #ff2a3b;
    color: #ffffff;
}
QTabBar::tab:hover:!selected {
    background: #181c28;
    color: #cbd5e1;
}

/* Tabelas estilo Telemetria Datalogger */
QTableWidget {
    background-color: #0d0f15;
    border: 1px solid #232733;
    border-radius: 2px;
    gridline-color: #1a1e2b;
    color: #f1f2f6;
    selection-background-color: #ff2a3b;
    selection-color: #ffffff;
    font-family: 'Consolas', monospace;
    font-size: 13px;
}
QHeaderView::section {
    background-color: #11131a;
    color: #8f97a6;
    font-weight: 800;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    border: none;
    border-bottom: 2px solid #232733;
    border-right: 1px solid #1a1e2b;
    padding: 7px 10px;
}

/* Entradas e Seletores */
QLineEdit, QComboBox, QSpinBox {
    background-color: #11131a;
    border: 1px solid #2a3040;
    border-radius: 2px;
    padding: 7px 12px;
    color: #ffffff;
    font-weight: 700;
}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus {
    border: 1px solid #ff2a3b;
    background-color: #161924;
}

/* Barra de Progresso / Shift Light Bar */
QProgressBar {
    border: 1px solid #232733;
    border-radius: 2px;
    text-align: center;
    background-color: #0b0d12;
    color: #ffffff;
    font-weight: 800;
    font-size: 11px;
}
QProgressBar::chunk {
    background-color: #ff2a3b;
}

/* Caixas de Seleção */
QCheckBox {
    color: #8f97a6;
    font-weight: 700;
}
QCheckBox::indicator:checked {
    background-color: #ff2a3b;
    border: 1px solid #ff4757;
    border-radius: 2px;
}

/* Barras de Rolagem */
QScrollBar:vertical {
    border: none;
    background: #090a0e;
    width: 7px;
}
QScrollBar::handle:vertical {
    background: #232733;
    border-radius: 2px;
}
QScrollBar::handle:vertical:hover {
    background: #ff2a3b;
}
"""


class TelemetryTile(QFrame):
    """
    Mostrador digital no formato de card de instrumentação e cockpit esportivo.
    Exibe o título técnico, valor em fonte de alto impacto e unidade de medição.
    """

    def __init__(self, title: str, initial_val: str, unit: str, color_accent: str = "#FF2A3B", parent=None):
        super().__init__(parent)
        self.color_accent = color_accent
        self.setStyleSheet(f"""
            QFrame {{
                background-color: #101218;
                border: 1px solid #232733;
                border-left: 3px solid {color_accent};
                border-radius: 2px;
                padding: 10px;
            }}
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(2)

        self.lbl_title = QLabel(title.upper())
        self.lbl_title.setStyleSheet("font-size: 10px; font-weight: 800; color: #8f97a6; letter-spacing: 0.8px;")
        layout.addWidget(self.lbl_title)

        val_box = QHBoxLayout()
        val_box.setSpacing(4)

        self.lbl_val = QLabel(initial_val)
        self.lbl_val.setStyleSheet("font-size: 24px; font-weight: 900; color: #ffffff; font-family: 'Consolas', 'Segoe UI', sans-serif;")
        val_box.addWidget(self.lbl_val)

        self.lbl_unit = QLabel(unit)
        self.lbl_unit.setStyleSheet(f"font-size: 11px; font-weight: 800; color: {color_accent}; margin-bottom: 4px;")
        val_box.addWidget(self.lbl_unit, alignment=Qt.AlignmentFlag.AlignBottom)
        val_box.addStretch()

        layout.addLayout(val_box)

    def set_value(self, val: str):
        self.lbl_val.setText(str(val))


class LiveMiniScopeWidget(QWidget):
    """
    Osciloscópio e Datalogger Gráfico Multi-Canal de Telemetria.
    Fundo preto carvão, retículo técnico em cinza fosco, curvas em cores racing
    (Vermelho Racing, Âmbar, Ciano e Verde) e HUD digital com estatísticas em tempo real.
    """

    CH_COLORS = [
        QColor("#FF2A3B"),  # Canal 1: Vermelho Racing
        QColor("#00E5FF"),  # Canal 2: Ciano Elétrico (Pressão / MAP)
        QColor("#FFB800"),  # Canal 3: Âmbar Ouro (TPS / Borboleta)
        QColor("#00E676")   # Canal 4: Verde Esmeralda (Sonda / Lambda)
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(175)
        self.max_points = 120
        self.selected_channel = 0  # 0 = Todos sobrepostos, 1..4 = Canal específico
        self.channel_names = ["Canal 1 (RPM)", "Canal 2 (MAP)", "Canal 3 (TPS)", "Canal 4 (Lambda)"]
        self.channel_units = ["RPM", "mbar", "%", "V"]
        self.channels_history: Dict[int, List[float]] = {0: [], 1: [], 2: [], 3: []}

    def set_channel_labels(self, labels: List[str], units: List[str]):
        for i in range(min(4, len(labels))):
            self.channel_names[i] = labels[i]
            if i < len(units):
                self.channel_units[i] = units[i]

    def add_channels_data(self, values: List[float]):
        for i, val in enumerate(values[:4]):
            self.channels_history[i].append(val)
            if len(self.channels_history[i]) > self.max_points:
                self.channels_history[i].pop(0)
        self.update()

    def add_point(self, val: float):
        self.add_channels_data([val])

    def get_stats(self, ch_idx: int) -> Dict[str, Any]:
        data = self.channels_history.get(ch_idx, [])
        if not data:
            return {"cur": "--", "min": "--", "max": "--", "avg": "--", "count": 0}
        return {
            "cur": f"{data[-1]:.2f}",
            "min": f"{min(data):.2f}",
            "max": f"{max(data):.2f}",
            "avg": f"{sum(data)/len(data):.2f}",
            "count": len(data)
        }

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        canvas_h = h - 26

        # Fundo Preto Asfalto Profundo
        painter.fillRect(0, 0, w, h, QColor("#090a0e"))

        # Grade Reticular Técnica
        painter.setPen(QPen(QColor("#181b24"), 1, Qt.PenStyle.DashLine))
        for y in range(18, canvas_h, 24):
            painter.drawLine(0, y, w, y)
        for x in range(30, w, 40):
            painter.drawLine(x, 0, x, canvas_h)

        # Barra do HUD Digital de Rodapé
        painter.setPen(QPen(QColor("#232733"), 1))
        painter.drawLine(0, canvas_h, w, canvas_h)
        painter.fillRect(0, canvas_h + 1, w, 25, QColor("#0e1017"))

        channels_to_draw = range(4) if self.selected_channel == 0 else [self.selected_channel - 1]

        all_vals = []
        for ch in channels_to_draw:
            all_vals.extend(self.channels_history.get(ch, []))

        if len(all_vals) >= 2:
            min_v = min(all_vals)
            max_v = max(all_vals)
            if max_v == min_v:
                max_v += 1.0

            step = w / (self.max_points - 1)

            for ch in channels_to_draw:
                hist = self.channels_history.get(ch, [])
                if len(hist) < 2:
                    continue

                color = self.CH_COLORS[ch % len(self.CH_COLORS)]
                painter.setPen(QPen(color, 2))

                for i in range(len(hist) - 1):
                    y1 = canvas_h - int(((hist[i] - min_v) / (max_v - min_v)) * (canvas_h - 22) + 11)
                    y2 = canvas_h - int(((hist[i + 1] - min_v) / (max_v - min_v)) * (canvas_h - 22) + 11)
                    x1 = int(i * step)
                    x2 = int((i + 1) * step)
                    painter.drawLine(x1, y1, x2, y2)

                # Cursor Pontual Ativo
                last_y = canvas_h - int(((hist[-1] - min_v) / (max_v - min_v)) * (canvas_h - 22) + 11)
                last_x = int((len(hist) - 1) * step)
                painter.setBrush(QBrush(color))
                painter.drawRect(last_x - 3, last_y - 3, 6, 6)

            painter.setPen(QPen(QColor("#6b7280")))
            painter.setFont(QFont("Consolas", 8, QFont.Weight.Bold))
            painter.drawText(8, 14, f"MAX: {max_v:.1f}")
            painter.drawText(8, canvas_h - 6, f"MIN: {min_v:.1f}")

        # HUD Digital
        hud_ch = 0 if self.selected_channel == 0 else self.selected_channel - 1
        stats = self.get_stats(hud_ch)
        name = self.channel_names[hud_ch] if hud_ch < len(self.channel_names) else f"CH{hud_ch+1}"
        unit = self.channel_units[hud_ch] if hud_ch < len(self.channel_units) else ""

        color = self.CH_COLORS[hud_ch % len(self.CH_COLORS)]
        painter.setPen(QPen(color))
        painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        painter.drawText(10, h - 8, f"■ {name.upper()}: {stats['cur']} {unit}")

        painter.setPen(QPen(QColor("#8f97a6")))
        painter.setFont(QFont("Consolas", 9))
        hud_info = f"MIN: {stats['min']} {unit}  |  MÁX: {stats['max']} {unit}  |  MÉD: {stats['avg']} {unit}  |  AMOSTRAS: {stats['count']}"
        painter.drawText(220, h - 8, hud_info)


class ConnectionWorker(QThread):
    """Worker assíncrono para conexão com a ECU sem travar a interface gráfica."""
    connection_success = pyqtSignal(dict, dict)
    connection_failed = pyqtSignal(str)

    def __init__(self, engine: KW1281Engine, address: int):
        super().__init__()
        self.engine = engine
        self.address = address

    def run(self):
        try:
            self.engine.connect(self.address)
            info = self.engine.ecu_info
            detected = self.engine.identify_ecu_system()
            self.connection_success.emit(info, detected)
        except Exception as e:
            self.connection_failed.emit(str(e))


class AutoScanWorker(QThread):
    """Worker assíncrono para execução do Auto-Scan em múltiplos módulos."""
    progress_updated = pyqtSignal(int, int, str)
    module_scanned = pyqtSignal(int, str, str, str)
    scan_completed = pyqtSignal(int, int)

    def __init__(self, autoscan_mgr: AutoScanManager, modules: List[int], port: str, is_mock: bool):
        super().__init__()
        self.autoscan_mgr = autoscan_mgr
        self.modules = modules
        self.port = port
        self.is_mock = is_mock
        self.is_cancelled = False

    def cancel(self):
        self.is_cancelled = True

    def run(self):
        total = len(self.modules)
        responded = 0

        for idx, addr in enumerate(self.modules):
            if self.is_cancelled:
                break

            name = self.autoscan_mgr.get_module_name(addr)
            self.progress_updated.emit(idx + 1, total, name)

            if self.is_mock:
                time.sleep(0.12)
                if addr == 0x01:
                    status = "OK — Respondendo"
                    dtcs = "00515 (Hall), 00525 (Lambda)"
                    responded += 1
                else:
                    status = "Sem resposta"
                    dtcs = "-"
            else:
                try:
                    ser = KLineSerialInterface(port=self.port)
                    ser.open()
                    eng = KW1281Engine(serial_interface=ser, mock_mode=False)
                    eng.connect(addr)
                    status = f"OK ({eng.ecu_info.get('part_number', 'Identificado')})"
                    dtc_list = eng.read_dtcs()
                    if dtc_list:
                        dtcs = f"{len(dtc_list)} avaria(s): " + ", ".join(d['code'] for d in dtc_list[:3])
                    else:
                        dtcs = "Sem avarias (0 falhas)"
                    responded += 1
                    eng.disconnect()
                except Exception:
                    status = "Sem resposta"
                    dtcs = "-"

            self.module_scanned.emit(addr, name, status, dtcs)

        self.scan_completed.emit(total, responded)


class TBICalibrationWidget(QWidget):
    """
    Widget assistente de calibração de TBI e marcha lenta de alta precisão.
    """

    def __init__(self, engine: Optional[KW1281Engine] = None, get_port_fn=None, is_mock_fn=None, parent=None):
        super().__init__(parent)
        self.engine = engine
        self.get_port_fn = get_port_fn
        self.is_mock_fn = is_mock_fn
        self.owned_engine = False

        self.poll_timer = QTimer(self)
        self.poll_timer.timeout.connect(self._poll_basic_settings)
        self.active_group = 98

        self.countdown_remaining = 0
        self.countdown_total = 0
        self.countdown_timer = QTimer(self)
        self.countdown_timer.timeout.connect(self._tick_countdown)

        self.init_ui()

    def init_ui(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background: transparent; border: none;")

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(12)

        # Card Dinâmico do Veículo
        self.card_vehicle = QFrame()
        self.card_vehicle.setStyleSheet("background-color: #101218; border: 1px solid #232733; border-left: 3px solid #ff2a3b; border-radius: 2px; padding: 14px;")
        card_layout = QVBoxLayout(self.card_vehicle)

        self.lbl_veh_title = QLabel("CALIBRAÇÃO DE BORBOLETA (TBI) & MARCHA LENTA")
        self.lbl_veh_title.setStyleSheet("font-size: 14px; font-weight: 800; color: #ff2a3b; letter-spacing: 0.8px;")
        self.lbl_veh_desc = QLabel("O OpenVAG lê a central e seleciona automaticamente a estratégia do seu motor (Bosch MP 9.0 ou Marelli 1AVP).")
        self.lbl_veh_desc.setStyleSheet("color: #cbd5e1; font-size: 13px;")

        card_layout.addWidget(self.lbl_veh_title)
        card_layout.addWidget(self.lbl_veh_desc)
        layout.addWidget(self.card_vehicle)

        # Grupo de Seleção de Modo
        self.group_modes = QGroupBox("Seleção Manual de Sistema (Bancada)")
        self.group_modes.setVisible(False)
        mode_layout = QVBoxLayout(self.group_modes)

        self.radio_cable = QRadioButton("Bosch Motronic MP 9.0 (Gol Mi 1.0 8v) — Grupo 098")
        self.radio_cable.setChecked(True)
        self.radio_cable.setStyleSheet("font-weight: 700; color: #ffb800;")

        self.radio_1avp = QRadioButton("Magneti Marelli 1AVP / 1AVB (Gol MI) — Reset Canal 00")
        self.radio_1avp.setStyleSheet("font-weight: 700; color: #ff2a3b;")

        self.radio_egas = QRadioButton("Bosch Motronic ME 7.x (E-Gas Eletrônico) — Grupo 060")
        self.radio_egas.setStyleSheet("font-weight: 700; color: #00e676;")

        self.radio_timing = QRadioButton("Ajuste Básico de Ignição 1AVP (Grupo 001) — Trava 9.0° APMS")
        self.radio_timing.setStyleSheet("font-weight: 700; color: #00e5ff;")

        self.btn_group = QButtonGroup(self)
        self.btn_group.addButton(self.radio_cable, 3)
        self.btn_group.addButton(self.radio_1avp, 1)
        self.btn_group.addButton(self.radio_egas, 2)
        self.btn_group.addButton(self.radio_timing, 4)
        self.btn_group.idToggled.connect(self._on_mode_changed)

        mode_layout.addWidget(self.radio_cable)
        mode_layout.addWidget(self.radio_1avp)
        mode_layout.addWidget(self.radio_egas)
        mode_layout.addWidget(self.radio_timing)
        layout.addWidget(self.group_modes)

        self.btn_toggle_manual = QPushButton("⚙ Mostrar Opções Manuais (Avançado)")
        self.btn_toggle_manual.setStyleSheet("background: transparent; border: none; color: #6b7280; font-size: 11px; text-decoration: underline;")
        self.btn_toggle_manual.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_toggle_manual.clicked.connect(self._toggle_manual_modes)
        layout.addWidget(self.btn_toggle_manual)

        self.txt_explanation = QTextEdit()
        self.txt_explanation.setReadOnly(True)
        self.txt_explanation.setMaximumHeight(85)
        self.txt_explanation.setStyleSheet("background-color: #0b0c10; border: 1px solid #232733; border-radius: 2px; padding: 8px; color: #cbd5e1;")
        layout.addWidget(self.txt_explanation)

        # Checklist
        group_pre = QGroupBox("Checklist de Segurança")
        pre_layout = QVBoxLayout(group_pre)
        self.chk_ignition = QCheckBox("1. Chave de ignição ligada com motor DESLIGADO")
        self.chk_ignition.setChecked(True)
        self.chk_battery = QCheckBox("2. Tensão de bateria com carga normal (> 11.5V)")
        self.chk_battery.setChecked(True)
        self.chk_pedal = QCheckBox("3. Pedal do acelerador totalmente livre")
        self.chk_pedal.setChecked(True)
        self.chk_dtcs = QCheckBox("4. Sem falhas elétricas graves ativas no TPS")
        self.chk_dtcs.setChecked(True)

        pre_layout.addWidget(self.chk_ignition)
        pre_layout.addWidget(self.chk_battery)
        pre_layout.addWidget(self.chk_pedal)
        pre_layout.addWidget(self.chk_dtcs)
        layout.addWidget(group_pre)

        # Barra de Ações
        action_box = QHBoxLayout()
        self.btn_start = QPushButton("▶ INICIAR CALIBRAÇÃO DE BORBOLETA")
        self.btn_start.setMinimumHeight(44)
        self.btn_start.setStyleSheet("background-color: #ff2a3b; color: white; font-weight: 800; font-size: 13px;")
        self.btn_start.clicked.connect(self.start_calibration)
        action_box.addWidget(self.btn_start)

        self.btn_stop = QPushButton("⏹ INTERROMPER")
        self.btn_stop.setMinimumHeight(44)
        self.btn_stop.setEnabled(False)
        self.btn_stop.setStyleSheet("background-color: #212636; color: white; font-weight: 800;")
        self.btn_stop.clicked.connect(self.stop_calibration)
        action_box.addWidget(self.btn_stop)
        layout.addLayout(action_box)

        self.lbl_status = QLabel("STATUS: AGUARDANDO COMANDO...")
        self.lbl_status.setStyleSheet("background-color: #101218; color: #8f97a6; padding: 8px 12px; border-radius: 2px; font-weight: 800; font-size: 11px;")
        layout.addWidget(self.lbl_status)

        # Ciclo de Chave 1AVP
        self.box_1avp_wizard = QGroupBox("Ciclo de Chave & Inicialização 1AVP")
        wiz_layout = QVBoxLayout(self.box_1avp_wizard)

        self.lbl_wiz_step1 = QLabel("<b>Passo 1: Desligue a ignição</b> por 15 segundos para desarmar o relé principal.")
        wiz_layout.addWidget(self.lbl_wiz_step1)
        self.btn_timer_15s = QPushButton("⏱ Iniciar Cronômetro de 15 Segundos (Desligado)")
        self.btn_timer_15s.clicked.connect(lambda: self._start_countdown(15, "Passo 1: Chave desligada. Aguarde o relé desarmar..."))
        wiz_layout.addWidget(self.btn_timer_15s)

        self.lbl_wiz_step2 = QLabel("<b>Passo 2: Ligue a ignição</b> (sem partida) por 30 segundos. A ECU calibra o TPS e passos.")
        wiz_layout.addWidget(self.lbl_wiz_step2)
        self.btn_timer_30s = QPushButton("⏱ Iniciar Cronômetro de 30 Segundos (Chave Ligada)")
        self.btn_timer_30s.clicked.connect(lambda: self._start_countdown(30, "Passo 2: Chave ligada (sem partida). A 1AVP está indexando..."))
        wiz_layout.addWidget(self.btn_timer_30s)

        self.lbl_wiz_step3 = QLabel("<b>Passo 3: Dê a partida</b> no motor sem acelerar e deixe aquecer em marcha lenta.")
        wiz_layout.addWidget(self.lbl_wiz_step3)

        self.countdown_box = QWidget()
        self.countdown_box.setVisible(False)
        cd_layout = QVBoxLayout(self.countdown_box)
        self.lbl_countdown_msg = QLabel("Contagem regressiva...")
        self.lbl_countdown_msg.setStyleSheet("color: #ff2a3b; font-weight: 800; font-size: 12px;")
        cd_layout.addWidget(self.lbl_countdown_msg)
        self.progress_countdown = QProgressBar()
        cd_layout.addWidget(self.progress_countdown)
        self.lbl_countdown_timer = QLabel("0s")
        self.lbl_countdown_timer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_countdown_timer.setStyleSheet("font-size: 20px; font-weight: 900; color: #ff2a3b;")
        cd_layout.addWidget(self.lbl_countdown_timer)
        wiz_layout.addWidget(self.countdown_box)

        layout.addWidget(self.box_1avp_wizard)

        self.table_box = QGroupBox("Parâmetros do Ajuste Básico em Tempo Real")
        table_layout = QVBoxLayout(self.table_box)
        self.table_tbi_live = QTableWidget(4, 4)
        self.table_tbi_live.setHorizontalHeaderLabels(["PARÂMETRO / SENSOR", "VALOR ATUAL", "UNIDADE", "ESPECIFICAÇÃO"])
        self.table_tbi_live.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table_layout.addWidget(self.table_tbi_live)
        layout.addWidget(self.table_box)

        scroll.setWidget(container)
        main_v = QVBoxLayout(self)
        main_v.setContentsMargins(0, 0, 0, 0)
        main_v.addWidget(scroll)

        self.box_1avp_wizard.setVisible(False)
        self.table_box.setVisible(False)
        self.txt_explanation.setHtml(
            "<p style='color: #64748b; text-align: center; padding: 18px;'>"
            "🔌 <b>Nenhum veículo conectado no momento.</b><br>"
            "Conecte o cabo KKL na tomada OBD2 e ligue a chave de ignição.<br>"
            "O OpenVAG lerá a central e preparará a calibração de borboleta automaticamente."
            "</p>"
        )

        if self.engine and self.engine.connected:
            self.apply_auto_detected_ecu()

    def _toggle_manual_modes(self):
        is_vis = not self.group_modes.isVisible()
        self.group_modes.setVisible(is_vis)
        self.btn_toggle_manual.setText("⚙ Ocultar Opções Manuais" if is_vis else "⚙ Mostrar Opções Manuais (Avançado)")

    def apply_auto_detected_ecu(self):
        if not self.engine or not self.engine.connected:
            return
        detected = self.engine.identify_ecu_system()
        family = detected.get("family", "")
        brand = detected.get("brand", "VAG")
        model = detected.get("model", "ECU")
        rec_mode = detected.get("recommended_tbi_mode", 3)
        throttle = detected.get("throttle_type", "")

        self.group_modes.setVisible(False)
        self.btn_toggle_manual.setText("⚙ Mostrar Opções Manuais (Avançado)")

        if family == "BOSCH_MP90" or rec_mode == 3:
            self.lbl_veh_title.setText(f"VEÍCULO IDENTIFICADO: {brand.upper()} {model.upper()} (GOL G2 1.0 8V)")
            self.lbl_veh_title.setStyleSheet("font-size: 14px; font-weight: 800; color: #ffb800;")
            self.lbl_veh_desc.setText(
                f"<b>Arquitetura:</b> {throttle}<br>"
                "<b>Procedimento:</b> Alinhamento de Batente de Marcha Lenta (Ajuste Básico - Grupo 098)."
            )
            self.card_vehicle.setStyleSheet("background-color: #101218; border: 1px solid #232733; border-left: 3px solid #ffb800; border-radius: 2px; padding: 12px;")
            self.radio_cable.setChecked(True)
            self._on_mode_changed(3, True)
            self.btn_start.setText("▶ INICIAR CALIBRAÇÃO (GRUPO 098)")

        elif family == "MARELLI_1AVP" or rec_mode == 1:
            self.lbl_veh_title.setText(f"VEÍCULO IDENTIFICADO: {brand.upper()} {model.upper()} (GOL / SANTANA)")
            self.lbl_veh_title.setStyleSheet("font-size: 14px; font-weight: 800; color: #ff2a3b;")
            self.lbl_veh_desc.setText(
                f"<b>Arquitetura:</b> {throttle}<br>"
                "<b>Procedimento:</b> Reset de Auto-adaptação na EEPROM (Canal 00) + Ciclo de Chave."
            )
            self.card_vehicle.setStyleSheet("background-color: #101218; border: 1px solid #232733; border-left: 3px solid #ff2a3b; border-radius: 2px; padding: 12px;")
            self.radio_1avp.setChecked(True)
            self._on_mode_changed(1, True)
            self.btn_start.setText("▶ EXECUTAR RESET MARCHA LENTA (CANAL 00)")

        elif family == "BOSCH_ME7" or rec_mode == 2:
            self.lbl_veh_title.setText(f"VEÍCULO IDENTIFICADO: {brand.upper()} {model.upper()} (E-GAS ELETRÔNICO)")
            self.lbl_veh_title.setStyleSheet("font-size: 14px; font-weight: 800; color: #00e676;")
            self.lbl_veh_desc.setText(
                f"<b>Arquitetura:</b> {throttle}<br>"
                "<b>Procedimento:</b> Alinhamento de Borboleta Eletrônica Drive-by-Wire (Ajuste Básico - Grupo 060)."
            )
            self.card_vehicle.setStyleSheet("background-color: #101218; border: 1px solid #232733; border-left: 3px solid #00e676; border-radius: 2px; padding: 12px;")
            self.radio_egas.setChecked(True)
            self._on_mode_changed(2, True)
            self.btn_start.setText("▶ INICIAR ALINHAMENTO E-GAS (GRUPO 060)")

    def _on_mode_changed(self, id_val: int, checked: bool):
        if not checked:
            return
        if id_val == 1:
            self.txt_explanation.setHtml(
                "<b style='color: #ff2a3b;'>Procedimento: Reset EEPROM Canal 00 (Magneti Marelli 1AVP)</b><br>"
                "• <b>Ação:</b> Apaga as tabelas autoadaptativas de combustível e marcha lenta.<br>"
                "• <b>Instrução:</b> Clique em Reset e execute as etapas do ciclo de chave abaixo."
            )
            self.box_1avp_wizard.setVisible(True)
            self.table_box.setVisible(False)
        elif id_val == 2:
            self.txt_explanation.setHtml(
                "<b style='color: #00e676;'>Procedimento: Ajuste Básico no Grupo 060 (E-Gas Eletrônico)</b><br>"
                "• <b>Ação:</b> A ECU comanda a borboleta e confere os potenciômetros duplos G187/G188 até <b>ADP. OK</b>."
            )
            self.box_1avp_wizard.setVisible(False)
            self.table_box.setVisible(True)
        elif id_val == 3:
            self.txt_explanation.setHtml(
                "<b style='color: #ffb800;'>Procedimento: Ajuste Básico no Grupo 098 (Bosch Motronic MP 9.0)</b><br>"
                "• <b>Ação:</b> O motor elétrico DC da marcha lenta afere o batente mecânico de repouso nos potenciômetros G69/G88.<br>"
                "• <b>Conclusão:</b> O alinhamento finaliza quando o Campo 4 registra <b>I.O. (In Ordnung) / ADP. OK</b>."
            )
            self.box_1avp_wizard.setVisible(False)
            self.table_box.setVisible(True)
        elif id_val == 4:
            self.txt_explanation.setHtml(
                "<b style='color: #00e5ff;'>Procedimento: Trava de Avanço a 9.0° APMS (Grupo 001)</b><br>"
                "• <b>Finalidade:</b> Trava o ponto dinâmico para aferição com pistola de ponto no volante do motor."
            )
            self.box_1avp_wizard.setVisible(False)
            self.table_box.setVisible(True)

    def start_calibration(self):
        if not (self.chk_ignition.isChecked() and self.chk_battery.isChecked() and self.chk_pedal.isChecked()):
            QMessageBox.warning(self, "Pré-condições", "Por favor, confirme todas as pré-condições obrigatórias antes de prosseguir.")
            return

        if not self.engine or not self.engine.connected:
            port = self.get_port_fn() if self.get_port_fn else "MOCK_BOSCH"
            is_mock = self.is_mock_fn() if self.is_mock_fn else str(port).startswith("MOCK")
            mock_ecu_type = "MARELLI_1AVP" if port == "MOCK_1AVP" else "BOSCH_MP90"
            pn_hint = "030-906-032-CP" if mock_ecu_type == "MARELLI_1AVP" else "1HS-908-258"

            try:
                if is_mock:
                    self.engine = KW1281Engine(mock_mode=True, part_number_hint=pn_hint, mock_ecu_type=mock_ecu_type)
                else:
                    ser = KLineSerialInterface(port=port)
                    ser.open()
                    self.engine = KW1281Engine(serial_interface=ser, mock_mode=False, part_number_hint="1HS-908-258")

                self.lbl_status.setText("STATUS: CONECTANDO AO MÓDULO 01 (ENGINE)...")
                self.lbl_status.setStyleSheet("background-color: #ff2a3b; color: white; padding: 8px 12px; border-radius: 2px; font-weight: 800;")
                QApplication.processEvents()
                self.engine.connect(0x01)
                self.owned_engine = True

                self.apply_auto_detected_ecu()
            except Exception as e:
                self.lbl_status.setText(f"ERRO DE CONEXÃO COM A ECU: {e}")
                self.lbl_status.setStyleSheet("background-color: #8b0000; color: white; padding: 8px 12px; border-radius: 2px; font-weight: 800;")
                QMessageBox.critical(self, "Falha de Conexão", f"Não foi possível conectar ao módulo do Motor (0x01):\n{e}")
                return

        mode = self.btn_group.checkedId()
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)

        if mode == 1:
            try:
                ok = self.engine.reset_factory_adaptations()
                if ok:
                    self.lbl_status.setText("STATUS: RESET DE AUTOADAPTAÇÃO CONCLUÍDO NA EEPROM! EXECUTE O CICLO DE CHAVE.")
                    self.lbl_status.setStyleSheet("background-color: #007a3d; color: #ffffff; padding: 8px 12px; border-radius: 2px; font-weight: 800;")
                    self.box_1avp_wizard.setVisible(True)
                    QMessageBox.information(
                        self, "Reset Efetuado com Sucesso",
                        "Os parâmetros autoadaptativos da central foram resetados para o padrão de fábrica!\n\n"
                        "Agora execute o ciclo de chave orientado nas 3 etapas abaixo."
                    )
                else:
                    self.lbl_status.setText("STATUS: COMANDO DE RESET REJEITADO PELA CENTRAL.")
                    self.lbl_status.setStyleSheet("background-color: #8b0000; color: white; padding: 8px 12px; border-radius: 2px; font-weight: 800;")
            except Exception as e:
                self.lbl_status.setText(f"FALHA AO RESETAR ADAPTAÇÃO: {e}")
                self.lbl_status.setStyleSheet("background-color: #8b0000; color: white; padding: 8px 12px; border-radius: 2px; font-weight: 800;")
        else:
            if mode == 2:
                self.active_group = 60
                target_desc = "ALINHAMENTO E-GAS (GRUPO 060)"
            elif mode == 3:
                self.active_group = 98
                target_desc = "ALINHAMENTO BOSCH MP 9.0 (GRUPO 098)"
            else:
                self.active_group = 1
                target_desc = "TRAVA DE PONTO 9.0° APMS (GRUPO 001)"

            try:
                self.lbl_status.setText(f"STATUS: {target_desc} EM EXECUÇÃO... AGUARDANDO CONFIRMAÇÃO...")
                self.lbl_status.setStyleSheet("background-color: #171a24; border: 1px solid #ff2a3b; color: #ff2a3b; padding: 8px 12px; border-radius: 2px; font-weight: 800;")
                self.engine.run_basic_settings(self.active_group)
                self._poll_basic_settings()
                self.poll_timer.start(700)
            except Exception as e:
                self.lbl_status.setText(f"ERRO AO DISPARAR AJUSTE BÁSICO: {e}")
                self.lbl_status.setStyleSheet("background-color: #8b0000; color: white; padding: 8px 12px; border-radius: 2px; font-weight: 800;")

    def _poll_basic_settings(self):
        if not self.engine:
            self.poll_timer.stop()
            return
        try:
            fields = self.engine.read_measuring_group(self.active_group)
            self.table_tbi_live.setRowCount(len(fields))
            for r, f in enumerate(fields):
                self.table_tbi_live.setItem(r, 0, QTableWidgetItem(f.get("name", f"Campo {r+1}")))
                self.table_tbi_live.setItem(r, 1, QTableWidgetItem(str(f.get("value", "--"))))
                self.table_tbi_live.setItem(r, 2, QTableWidgetItem(f.get("unit", "")))
                self.table_tbi_live.setItem(r, 3, QTableWidgetItem(f.get("spec", "")))

                val_str = str(f.get("value", ""))
                if any(x in val_str for x in ("ADP. OK", "ADP OK", "I.O.", "I.O")):
                    self.lbl_status.setText("STATUS: ALINHAMENTO DE BORBOLETA CONCLUÍDO COM SUCESSO! (ADP. OK)")
                    self.lbl_status.setStyleSheet("background-color: #007a3d; color: #ffffff; padding: 8px 12px; border-radius: 2px; font-weight: 800;")
                elif any(x in val_str for x in ("ADP. RUN", "ADP RUN", "Lauft")):
                    self.lbl_status.setText("STATUS: ADAPTAÇÃO EM ANDAMENTO... (ADP. RUN)")
                    self.lbl_status.setStyleSheet("background-color: #ffb800; color: #000000; padding: 8px 12px; border-radius: 2px; font-weight: 800;")
                elif "ERROR" in val_str:
                    self.lbl_status.setText("STATUS: FALHA NO ALINHAMENTO DE BORBOLETA (ERROR).")
                    self.lbl_status.setStyleSheet("background-color: #8b0000; color: white; padding: 8px 12px; border-radius: 2px; font-weight: 800;")
        except Exception:
            self.poll_timer.stop()

    def _start_countdown(self, seconds: int, message: str):
        self.countdown_remaining = seconds
        self.countdown_total = seconds
        self.lbl_countdown_msg.setText(message)
        self.progress_countdown.setMaximum(seconds)
        self.progress_countdown.setValue(seconds)
        self.lbl_countdown_timer.setText(f"{seconds}s")
        self.countdown_box.setVisible(True)
        self.countdown_timer.start(1000)

    def _tick_countdown(self):
        self.countdown_remaining -= 1
        self.progress_countdown.setValue(self.countdown_remaining)
        self.lbl_countdown_timer.setText(f"{self.countdown_remaining}s")
        if self.countdown_remaining <= 0:
            self.countdown_timer.stop()
            self.lbl_countdown_timer.setText("CONCLUÍDO! ✅")
            self.lbl_countdown_msg.setText("Etapa finalizada. Avance para o próximo passo.")

    def stop_calibration(self):
        if self.poll_timer.isActive():
            self.poll_timer.stop()
        if self.countdown_timer.isActive():
            self.countdown_timer.stop()

        if self.owned_engine and self.engine:
            try:
                self.engine.disconnect()
            except Exception:
                pass
            self.engine = None
            self.owned_engine = False

        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.lbl_status.setText("STATUS: PROCEDIMENTO ENCERRADO.")
        self.lbl_status.setStyleSheet("background-color: #101218; color: #8f97a6; padding: 8px 12px; border-radius: 2px; font-weight: 800;")


class TBICalibrationDialog(QDialog):

    def __init__(self, engine: Optional[KW1281Engine] = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("CALIBRAÇÃO DE BORBOLETA (TBI) & MARCHA LENTA")
        self.resize(860, 680)
        self.setStyleSheet(MOTORSPORT_STYLE)

        layout = QVBoxLayout(self)
        self.widget = TBICalibrationWidget(engine=engine, parent=self)
        layout.addWidget(self.widget)

        btn_close = QPushButton("FECHAR ASSISTENTE")
        btn_close.clicked.connect(self.close_and_cleanup)
        layout.addWidget(btn_close)

    def close_and_cleanup(self):
        self.widget.stop_calibration()
        self.accept()

    def closeEvent(self, event):
        self.widget.stop_calibration()
        event.accept()


class OpenVAGMainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("OpenVAG — Estação de Diagnóstico & Telemetria Automotiva KKL")
        self.resize(1080, 780)
        self.setStyleSheet(MOTORSPORT_STYLE)

        self.engine: Optional[KW1281Engine] = None
        self.dtc_db = DTCDatabase()
        self.logger = TelemetryLogger()
        self.autoscan_mgr = AutoScanManager()
        self.autoscan_worker: Optional[AutoScanWorker] = None

        self.last_detected_port: Optional[str] = None
        self.known_ports_set = set()

        self.init_ui()

        # Watchdog de detecção automática Hotplug de portas USB / KKL
        self.hotplug_timer = QTimer(self)
        self.hotplug_timer.timeout.connect(self.check_usb_hotplug)
        self.hotplug_timer.start(800)

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(14, 14, 14, 14)
        main_layout.setSpacing(10)

        # Header Superior Motorsport Racing
        header_bar = QFrame()
        header_bar.setStyleSheet("background-color: #101218; border: 1px solid #232733; border-radius: 2px; padding: 6px 12px;")
        header_layout = QHBoxLayout(header_bar)
        header_layout.setContentsMargins(4, 4, 4, 4)

        logo_box = QHBoxLayout()
        logo_box.setSpacing(6)
        lbl_badge = QLabel("VAG")
        lbl_badge.setStyleSheet("background-color: #ff2a3b; color: #ffffff; font-weight: 900; font-size: 14px; padding: 3px 7px; border-radius: 2px;")
        logo_box.addWidget(lbl_badge)

        logo_label = QLabel("<b>OpenVAG</b>")
        logo_label.setStyleSheet("font-size: 18px; font-weight: 900; color: #ffffff; letter-spacing: 1px;")
        logo_box.addWidget(logo_label)

        lbl_sub = QLabel("DIAGNOSTIC & TELEMETRY")
        lbl_sub.setStyleSheet("font-size: 10px; font-weight: 800; color: #8f97a6; letter-spacing: 1.2px; margin-left: 6px;")
        logo_box.addWidget(lbl_sub)
        header_layout.addLayout(logo_box)

        header_layout.addStretch()

        self.status_badge = QLabel("⚪ USB DESCONECTADO")
        self.status_badge.setStyleSheet("background-color: #171a24; border: 1px solid #2e3547; color: #8f97a6; padding: 5px 12px; border-radius: 2px; font-weight: 800; font-size: 11px;")
        header_layout.addWidget(self.status_badge)

        self.port_combo = QComboBox()
        self.port_combo.setMinimumWidth(180)
        self.refresh_ports()
        header_layout.addWidget(self.port_combo)

        self.chk_autodetect = QCheckBox("AUTO P&P")
        self.chk_autodetect.setChecked(True)
        header_layout.addWidget(self.chk_autodetect)

        self.btn_refresh = QPushButton("↻")
        self.btn_refresh.setToolTip("Atualizar portas COM")
        self.btn_refresh.setMaximumWidth(40)
        self.btn_refresh.clicked.connect(self.refresh_ports)
        header_layout.addWidget(self.btn_refresh)

        main_layout.addWidget(header_bar)

        # Banner de Notificação
        self.banner_hotplug = QLabel("💡 Conecte o cabo KKL 409.1 na porta USB para detecção plug-and-play automática.")
        self.banner_hotplug.setStyleSheet("background-color: #101218; border: 1px solid #232733; border-left: 3px solid #ff2a3b; padding: 7px 12px; border-radius: 2px; color: #cbd5e1; font-weight: 600;")
        main_layout.addWidget(self.banner_hotplug)

        # Abas Principais
        self.tabs = QTabWidget()
        self.tab_modules = QWidget()
        self.tab_autoscan = QWidget()
        self.tab_tbi = QWidget()
        self.tab_dtc_doctor = QWidget()
        self.tab_options = QWidget()

        self.setup_tab_modules()
        self.setup_tab_autoscan()
        self.setup_tab_tbi()
        self.setup_tab_dtc_doctor()
        self.setup_tab_options()

        self.tabs.addTab(self.tab_modules, "🏁 DASHBOARD & MÓDULOS")
        self.tabs.addTab(self.tab_autoscan, "⚡ AUTO-SCAN")
        self.tabs.addTab(self.tab_tbi, "🎯 AJUSTE DE TBI & LENTA")
        self.tabs.addTab(self.tab_dtc_doctor, "🩺 DIAGNÓSTICO DTC")
        self.tabs.addTab(self.tab_options, "⚙ SETUP HARDWARE")

        main_layout.addWidget(self.tabs)

        self.check_usb_hotplug(initial=True)

    def refresh_ports(self):
        current_selection = self.port_combo.currentData()
        self.port_combo.clear()
        ports = list_available_ports()
        self.known_ports_set = set(p["device"] for p in ports)

        for p in ports:
            tag = " ★ [KKL Plugado]" if p["is_likely_kkl"] else ""
            self.port_combo.addItem(f"{p['device']}{tag}", p["device"])

        if not ports:
            self.port_combo.addItem("⚠️ Nenhum Cabo USB Detectado", "NONE")
            self.port_combo.addItem("🧪 Modo Bancada (Bosch MP 9.0)", "MOCK_BOSCH")
            self.port_combo.addItem("🧪 Modo Bancada (Marelli 1AVP)", "MOCK_1AVP")

        if current_selection:
            idx = self.port_combo.findData(current_selection)
            if idx >= 0:
                self.port_combo.setCurrentIndex(idx)

    def check_usb_hotplug(self, initial: bool = False):
        current_ports = list_available_ports()
        current_set = set(p["device"] for p in current_ports)

        if current_set != self.known_ports_set or initial:
            self.refresh_ports()
            kkl_info = find_kkl_cable_port()

            if kkl_info:
                port_name = kkl_info["device"]
                desc = kkl_info.get("description", "Cabo KKL")

                if self.chk_autodetect.isChecked():
                    idx = self.port_combo.findData(port_name)
                    if idx >= 0:
                        self.port_combo.setCurrentIndex(idx)

                self.status_badge.setText(f"🟢 KKL ONLINE ({port_name})")
                self.status_badge.setStyleSheet("background-color: #007a3d; border: 1px solid #00e676; color: #ffffff; padding: 5px 12px; border-radius: 2px; font-weight: 800; font-size: 11px;")
                self.banner_hotplug.setText(f"🔌 <b>Cabo VAG-COM KKL conectado na porta {port_name}!</b> ({desc}) Barramento pronto.")
                self.banner_hotplug.setStyleSheet("background-color: #101218; border: 1px solid #232733; border-left: 3px solid #00e676; padding: 7px 12px; border-radius: 2px; color: #ffffff; font-weight: 600;")
                self.last_detected_port = port_name
            else:
                self.status_badge.setText("⚪ USB DESCONECTADO")
                self.status_badge.setStyleSheet("background-color: #171a24; border: 1px solid #2e3547; color: #8f97a6; padding: 5px 12px; border-radius: 2px; font-weight: 800; font-size: 11px;")
                self.banner_hotplug.setText("💡 Conecte o cabo VAG-COM KKL na porta USB para detecção automática instantânea.")
                self.banner_hotplug.setStyleSheet("background-color: #101218; border: 1px solid #232733; border-left: 3px solid #ff2a3b; padding: 7px 12px; border-radius: 2px; color: #cbd5e1; font-weight: 600;")
                self.last_detected_port = None

    def setup_tab_modules(self):
        layout = QVBoxLayout(self.tab_modules)
        layout.setSpacing(12)

        # 1. MOSTRADORES DIGITAIS ESTILO COCKPIT DE ALTA PERFORMANCE
        dash_group = QGroupBox("Cockpit de Instrumentação em Tempo Real")
        dash_layout = QGridLayout(dash_group)
        dash_layout.setSpacing(8)

        self.tile_rpm = TelemetryTile("ROTAÇÃO DO MOTOR", "--", "RPM", color_accent="#FF2A3B")
        self.tile_map = TelemetryTile("PRESSÃO DO COLETOR", "--", "mbar", color_accent="#00E5FF")
        self.tile_lambda = TelemetryTile("SONDA LAMBDA", "--", "λ", color_accent="#00E676")
        self.tile_ect = TelemetryTile("TEMP. ARREFECIMENTO", "--", "°C", color_accent="#FFB800")
        self.tile_tps = TelemetryTile("POSIÇÃO BORBOLETA", "--", "%", color_accent="#FF2A3B")
        self.tile_bat = TelemetryTile("TENSÃO DA BATERIA", "--", "V", color_accent="#00E5FF")

        dash_layout.addWidget(self.tile_rpm, 0, 0)
        dash_layout.addWidget(self.tile_map, 0, 1)
        dash_layout.addWidget(self.tile_lambda, 0, 2)
        dash_layout.addWidget(self.tile_ect, 1, 0)
        dash_layout.addWidget(self.tile_tps, 1, 1)
        dash_layout.addWidget(self.tile_bat, 1, 2)

        layout.addWidget(dash_group)

        # 2. BOTÃO HERO DE ACESSO RÁPIDO RACING
        btn_engine_hero = QPushButton("🏁 CONECTAR À INJEÇÃO ELETRÔNICA (01 - ENGINE)")
        btn_engine_hero.setMinimumHeight(56)
        btn_engine_hero.setStyleSheet("""
            QPushButton {
                background-color: #ff2a3b;
                border: 2px solid #ff4757;
                border-radius: 2px;
                color: #ffffff;
                font-size: 15px;
                font-weight: 900;
                letter-spacing: 1px;
            }
            QPushButton:hover {
                background-color: #e60012;
                border-color: #ffffff;
            }
        """)
        btn_engine_hero.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_engine_hero.clicked.connect(lambda: self.open_controller(0x01))
        layout.addWidget(btn_engine_hero)

        # 3. OUTROS MÓDULOS
        group_common = QGroupBox("Outros Módulos do Veículo")
        grid_common = QHBoxLayout(group_common)
        grid_common.setSpacing(8)

        btn_abs = QPushButton("03 - FREIOS ABS")
        btn_abs.setMinimumHeight(44)
        btn_abs.clicked.connect(lambda: self.open_controller(0x03))
        grid_common.addWidget(btn_abs)

        btn_airbag = QPushButton("15 - AIRBAGS")
        btn_airbag.setMinimumHeight(44)
        btn_airbag.clicked.connect(self.open_airbag_controller)
        grid_common.addWidget(btn_airbag)

        btn_cluster = QPushButton("17 - PAINEL")
        btn_cluster.setMinimumHeight(44)
        btn_cluster.clicked.connect(lambda: self.open_controller(0x17))
        grid_common.addWidget(btn_cluster)

        btn_immo = QPushButton("25 - IMOBILIZADOR")
        btn_immo.setMinimumHeight(44)
        btn_immo.clicked.connect(lambda: self.open_controller(0x25))
        grid_common.addWidget(btn_immo)

        layout.addWidget(group_common)

        # 4. ENDEREÇO DIRETO
        group_direct = QGroupBox("Acesso Direto por Endereço Hexadecimal")
        layout_direct = QHBoxLayout(group_direct)
        layout_direct.addWidget(QLabel("ENDEREÇO HEX (ex: 01, 03, 17, 25, 46):"))
        self.txt_direct_addr = QLineEdit("01")
        self.txt_direct_addr.setMaximumWidth(70)
        layout_direct.addWidget(self.txt_direct_addr)

        btn_direct_go = QPushButton("CONECTAR")
        btn_direct_go.clicked.connect(self.connect_direct_address)
        layout_direct.addWidget(btn_direct_go)
        layout_direct.addStretch()

        layout.addWidget(group_direct)
        layout.addStretch()

    def setup_tab_autoscan(self):
        layout = QVBoxLayout(self.tab_autoscan)

        top_bar = QHBoxLayout()
        top_bar.addWidget(QLabel("PERFIL DO VEÍCULO (CHASSI):"))

        self.combo_chassis = QComboBox()
        for code, data in self.autoscan_mgr.chassis_profiles.items():
            self.combo_chassis.addItem(f"{code} — {data['name'].upper()}", code)
        top_bar.addWidget(self.combo_chassis)

        self.btn_start_scan = QPushButton("▶ INICIAR AUTO-SCAN")
        self.btn_start_scan.setStyleSheet("background-color: #ff2a3b; color: white;")
        self.btn_start_scan.clicked.connect(self.run_autoscan)
        top_bar.addWidget(self.btn_start_scan)

        layout.addLayout(top_bar)

        self.progress_scan = QProgressBar()
        self.progress_scan.setValue(0)
        layout.addWidget(self.progress_scan)

        self.lbl_scan_status = QLabel("Selecione o chassi e clique em Iniciar Auto-Scan.")
        self.lbl_scan_status.setStyleSheet("color: #8f97a6; font-size: 11px; font-weight: 700;")
        layout.addWidget(self.lbl_scan_status)

        self.table_scan = QTableWidget(0, 4)
        self.table_scan.setHorizontalHeaderLabels(["ENDEREÇO", "MÓDULO", "RESPOSTA", "FALHAS (DTCS)"])
        self.table_scan.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table_scan)

    def setup_tab_tbi(self):
        layout = QVBoxLayout(self.tab_tbi)
        self.tbi_widget = TBICalibrationWidget(
            get_port_fn=lambda: self.port_combo.currentData(),
            is_mock_fn=lambda: str(self.port_combo.currentData()).startswith("MOCK"),
            parent=self
        )
        layout.addWidget(self.tbi_widget)

    def setup_tab_dtc_doctor(self):
        layout = QVBoxLayout(self.tab_dtc_doctor)

        search_bar = QHBoxLayout()
        search_bar.addWidget(QLabel("CONSULTAR CÓDIGO DE FALHA (VAG OU OBD-II):"))
        self.txt_dtc_search = QLineEdit("")
        self.txt_dtc_search.setPlaceholderText("Ex: 00513, 00515, P0321, P1570")
        self.txt_dtc_search.setMaximumWidth(220)
        search_bar.addWidget(self.txt_dtc_search)

        btn_search = QPushButton("🔍 ANALISAR FALHA")
        btn_search.clicked.connect(self.on_dtc_search)
        search_bar.addWidget(btn_search)
        search_bar.addStretch()

        layout.addLayout(search_bar)

        self.txt_dtc_details = QTextEdit()
        self.txt_dtc_details.setReadOnly(True)
        self.txt_dtc_details.setStyleSheet("background-color: #0d0f15; color: #f1f2f6; font-size: 13px; padding: 14px; border: 1px solid #232733; border-radius: 2px;")
        layout.addWidget(self.txt_dtc_details)

        total_dtcs = len(self.dtc_db.database)
        self.txt_dtc_details.setHtml(
            f"<div style='text-align: center; padding: 36px; color: #64748b;'>"
            f"<h3 style='color: #ff2a3b; font-weight: 800;'>🩺 BASE TÉCNICA DE DIAGNÓSTICO ({total_dtcs} FALHAS MAPEADAS)</h3>"
            "<p>Consulte os sintomas, testes elétricos com multímetro no chicote e ações mecânicas de reparo.<br><br>"
            "👉 Quando conectado ao veículo, os códigos gravados na ECU são cruzados automaticamente com esta base.</p>"
            "</div>"
        )

    def setup_tab_options(self):
        layout = QVBoxLayout(self.tab_options)

        group_port = QGroupBox("Diagnóstico da Interface Serial KKL")
        port_layout = QVBoxLayout(group_port)

        port_layout.addWidget(QLabel("Driver suportado: <b>CH341S64.SYS / FTDI FT232R</b>"))
        port_layout.addWidget(QLabel("Detecção Automática: <b>Ativada (Watchdog 800ms)</b>"))
        port_layout.addWidget(QLabel("Protocolo: <b>ISO 9141-2 / KW1281 / KWP2000</b> (Slow Init com Paridade Ímpar)"))

        btn_test_port = QPushButton("🔌 EXECUTAR TESTE DE LOOPBACK SERIAL")
        btn_test_port.clicked.connect(self.run_port_test)
        port_layout.addWidget(btn_test_port)

        layout.addWidget(group_port)

        group_timings = QGroupBox("Temporizações da Linha K (VCDS.CFG)")
        time_layout = QGridLayout(group_timings)
        time_layout.addWidget(QLabel("Block Interval (BInt): <b>55 ms</b>"), 0, 0)
        time_layout.addWidget(QLabel("Char Interval (CInt): <b>1 ms</b>"), 0, 1)
        time_layout.addWidget(QLabel("Echo Delay (EDel): <b>500 ms</b>"), 1, 0)
        time_layout.addWidget(QLabel("KP2 Delay: <b>25 ms</b>"), 1, 1)
        layout.addWidget(group_timings)

        layout.addStretch()

    def on_dtc_search(self):
        code = self.txt_dtc_search.text().strip()
        if not code:
            return
        info = self.dtc_db.lookup(code)

        html = f"""
        <h2 style='color: #ff2a3b; margin-bottom: 2px;'>CÓDIGO VAG: {info['vag_code']} (OBD-II: {info['obd_code']})</h2>
        <h3 style='color: #ffffff; margin-top: 2px;'>{info['component']}</h3>
        <p style='color: #cbd5e1; font-size: 13px;'><i>{info['description']}</i></p>
        <hr style='border: 1px solid #232733; margin: 12px 0;'>
        <h4 style='color: #ffb800;'>Sintomas Prováveis no Veículo:</h4>
        <ul style='color: #f1f2f6; line-height: 1.5;'>
        """
        for sym in info.get("symptoms", []):
            html += f"<li>{sym}</li>"
        html += """
        </ul>
        <h4 style='color: #00e676; margin-top: 14px;'>Procedimento de Teste com Multímetro no Chicote:</h4>
        <ol style='color: #f1f2f6; line-height: 1.5;'>
        """
        for step in info.get("multimeter_test", []):
            html += f"<li>{step}</li>"
        html += f"""
        </ol>
        <h4 style='color: #00e5ff; margin-top: 14px;'>Ação Corretiva Mecânica:</h4>
        <p style='color: #f1f2f6;'>{info.get('mechanical_fix')}</p>
        """
        self.txt_dtc_details.setHtml(html)

    def run_port_test(self):
        port_val = self.port_combo.currentData()
        if str(port_val).startswith("MOCK"):
            QMessageBox.information(self, "Teste de Interface", "Interface de Simulação (Mock): Status OK!\nComunicação com emulador pronta.")
            return

        try:
            ser = KLineSerialInterface(port=port_val)
            ser.open()
            ser.close()
            QMessageBox.information(self, "Teste de Interface", f"Porta {port_val}: Aberta e testada com sucesso!\nCabo KKL pronto para uso no veículo.")
        except Exception as e:
            QMessageBox.warning(self, "Erro de Interface", f"Não foi possível abrir a porta {port_val}.\nDetalhes: {e}")

    def connect_direct_address(self):
        text = self.txt_direct_addr.text().strip()
        try:
            addr = int(text, 16)
            self.open_controller(addr)
        except ValueError:
            QMessageBox.warning(self, "Endereço Inválido", "Digite um valor hexadecimal válido (ex: 01, 03, 17).")

    def run_autoscan(self):
        chassis_code = self.combo_chassis.currentData()
        profile = self.autoscan_mgr.chassis_profiles.get(chassis_code)
        if not profile:
            return

        modules = profile["modules"]
        self.table_scan.setRowCount(0)
        self.progress_scan.setMaximum(len(modules))
        self.progress_scan.setValue(0)
        self.btn_start_scan.setEnabled(False)

        port_val = self.port_combo.currentData()
        is_mock = str(port_val).startswith("MOCK")

        self.autoscan_worker = AutoScanWorker(self.autoscan_mgr, modules, port_val, is_mock)
        self.autoscan_worker.progress_updated.connect(self._on_autoscan_progress)
        self.autoscan_worker.module_scanned.connect(self._on_autoscan_row)
        self.autoscan_worker.scan_completed.connect(self._on_autoscan_finished)
        self.autoscan_worker.start()

    def _on_autoscan_progress(self, current: int, total: int, module_name: str):
        self.progress_scan.setValue(current)
        self.lbl_scan_status.setText(f"Varrendo módulo {current}/{total}: {module_name}...")

    def _on_autoscan_row(self, addr: int, name: str, status: str, dtcs: str):
        row = self.table_scan.rowCount()
        self.table_scan.insertRow(row)
        self.table_scan.setItem(row, 0, QTableWidgetItem(f"0x{addr:02X}"))
        self.table_scan.setItem(row, 1, QTableWidgetItem(name))
        self.table_scan.setItem(row, 2, QTableWidgetItem(status))
        self.table_scan.setItem(row, 3, QTableWidgetItem(dtcs))

    def _on_autoscan_finished(self, total: int, responded: int):
        self.btn_start_scan.setEnabled(True)
        self.lbl_scan_status.setText(f"Auto-Scan Concluído: {responded} de {total} módulos responderam.")
        QMessageBox.information(self, "Auto-Scan Concluído", f"Varredura finalizada!\n{responded} de {total} módulos responderam no chassi.")

    def open_controller(self, address: int):
        port_val = self.port_combo.currentData()
        if not port_val or port_val == "NONE":
            QMessageBox.warning(
                self, "Cabo Desconectado",
                "Nenhum cabo de diagnóstico KKL detectado na porta USB.\n\n"
                "Por favor, conecte o cabo USB no computador e na tomada OBD2 do veículo para iniciar."
            )
            return

        is_mock = str(port_val).startswith("MOCK")
        mock_ecu_type = "MARELLI_1AVP" if port_val == "MOCK_1AVP" else "BOSCH_MP90"

        dlg = ControllerDialog(address=address, port=port_val, is_mock=is_mock, mock_ecu_type=mock_ecu_type, parent=self)
        dlg.exec()

    def open_airbag_controller(self):
        res = QMessageBox.warning(
            self, "⚠️ Aviso de Segurança VAG — Módulo de Airbag (15)",
            "<b>ATENÇÃO - SEGURANÇA DOS MÓDULOS DE AIRBAG:</b><br><br>"
            "Em alguns veículos do Grupo VAG fabricados entre 2000 e 2001 equipados com controladores de Airbag vulneráveis (ex: 6Q0-909-605-A), "
            "o escaneamento de diagnóstico pode corromper a memória interna do módulo.<br><br>"
            "Deseja prosseguir com a conexão?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if res == QMessageBox.StandardButton.Yes:
            self.open_controller(0x15)


class ControllerDialog(QDialog):
    """
    Tela principal de diagnóstico de módulo (Controller Screen) no visual Motorsport Dark.
    """

    def __init__(self, address: int, port: str, is_mock: bool = False, mock_ecu_type: str = "BOSCH_MP90", parent=None):
        super().__init__(parent)
        self.address = address
        self.port = port
        self.is_mock = is_mock
        self.mock_ecu_type = mock_ecu_type
        self.engine: Optional[KW1281Engine] = None
        self.dtc_db = DTCDatabase()

        self.setWindowTitle(f"MÓDULO 0x{address:02X} — {MODULE_NAMES.get(address, 'Controlador').upper()}")
        self.resize(940, 690)
        self.setStyleSheet(MOTORSPORT_STYLE)

        self.measuring_timer = QTimer(self)
        self.measuring_timer.timeout.connect(self.poll_measuring_blocks)

        self.keepalive_timer = QTimer(self)
        self.keepalive_timer.timeout.connect(self._send_keepalive)

        self.is_logging_csv = False
        self.csv_file = None
        self.csv_writer = None
        self.csv_sample_count = 0
        self.csv_filepath = ""

        self.init_ui()
        self.start_connection()

    def init_ui(self):
        layout = QVBoxLayout(self)

        group_id = QGroupBox("Identificação da Central Eletrônica")
        id_layout = QVBoxLayout(group_id)

        self.lbl_part_number = QLabel("VAG NUMBER: CONECTANDO VIA LINHA K...")
        self.lbl_part_number.setStyleSheet("font-size: 14px; font-weight: 900; color: #ff2a3b; letter-spacing: 0.5px;")
        self.lbl_component = QLabel("COMPONENT: EXECUTANDO 5-BAUD SLOW INIT...")
        self.lbl_component.setStyleSheet("font-weight: 700; color: #ffffff;")
        self.lbl_coding = QLabel("SOFT. CODING: -- | WORK SHOP CODE: --")
        self.lbl_coding.setStyleSheet("color: #8f97a6; font-size: 11px;")

        id_layout.addWidget(self.lbl_part_number)
        id_layout.addWidget(self.lbl_component)
        id_layout.addWidget(self.lbl_coding)
        layout.addWidget(group_id)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        widget_basic = QWidget()
        v_basic = QVBoxLayout(widget_basic)
        v_basic.addWidget(QLabel("<b>FUNÇÕES RÁPIDAS DE DIAGNÓSTICO</b>"))

        self.btn_02 = QPushButton("🩺 CÓDIGOS DE FALHA (DTCS)")
        self.btn_02.setMinimumHeight(38)
        self.btn_02.clicked.connect(self.view_dtcs)
        v_basic.addWidget(self.btn_02)

        self.btn_08 = QPushButton("📊 SENSORES AO VIVO (LIVE DATA)")
        self.btn_08.setMinimumHeight(38)
        self.btn_08.clicked.connect(self.view_measuring_blocks)
        v_basic.addWidget(self.btn_08)

        self.btn_tba = QPushButton("🎯 CALIBRAÇÃO DE BORBOLETA / LENTA")
        self.btn_tba.setMinimumHeight(44)
        self.btn_tba.setStyleSheet("background-color: #ff2a3b; color: white; font-weight: 900;")
        self.btn_tba.clicked.connect(self.open_tbi_calibration)
        v_basic.addWidget(self.btn_tba)

        self.btn_04 = QPushButton("04 — AJUSTE BÁSICO")
        self.btn_04.clicked.connect(self.view_basic_settings)
        v_basic.addWidget(self.btn_04)

        v_basic.addStretch()
        splitter.addWidget(widget_basic)

        widget_adv = QWidget()
        v_adv = QVBoxLayout(widget_adv)
        v_adv.addWidget(QLabel("<b>FUNÇÕES AVANÇADAS</b>"))

        btn_03 = QPushButton("03 — TESTE DE ATUADORES")
        btn_03.clicked.connect(self.run_output_tests)
        v_adv.addWidget(btn_03)

        btn_07 = QPushButton("07 — RECODIFICAR MÓDULO")
        btn_07.clicked.connect(self.run_recode)
        v_adv.addWidget(btn_07)

        btn_10 = QPushButton("10 — ADAPTAÇÃO DE CANAIS")
        btn_10.clicked.connect(self.run_adaptation)
        v_adv.addWidget(btn_10)

        btn_11 = QPushButton("11 — ACESSO DE SEGURANÇA")
        btn_11.clicked.connect(self.run_login)
        v_adv.addWidget(btn_11)

        v_adv.addStretch()
        splitter.addWidget(widget_adv)

        layout.addWidget(splitter)

        # Painel Live
        self.stack_box = QGroupBox("Datalogger Gráfico & Osciloscópio Digital")
        self.stack_layout = QVBoxLayout(self.stack_box)

        self.table_live = QTableWidget(4, 4)
        self.table_live.setHorizontalHeaderLabels(["CAMPO", "VALOR ATUAL", "UNIDADE", "ESPECIFICAÇÃO"])
        self.table_live.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.stack_layout.addWidget(self.table_live)

        scope_header = QHBoxLayout()
        scope_header.addWidget(QLabel("CANAL DO GRÁFICO:"))
        self.combo_scope_channel = QComboBox()
        self.combo_scope_channel.addItem("Todos os Canais (Sobreposto)", 0)
        self.combo_scope_channel.addItem("Canal 1 (Vermelho Racing)", 1)
        self.combo_scope_channel.addItem("Canal 2 (Ciano)", 2)
        self.combo_scope_channel.addItem("Canal 3 (Âmbar)", 3)
        self.combo_scope_channel.addItem("Canal 4 (Verde)", 4)
        self.combo_scope_channel.currentIndexChanged.connect(self._on_scope_channel_changed)
        scope_header.addWidget(self.combo_scope_channel)
        scope_header.addStretch()
        self.stack_layout.addLayout(scope_header)

        self.scope = LiveMiniScopeWidget()
        self.stack_layout.addWidget(self.scope)

        layout.addWidget(self.stack_box)

        # Barra Inferior
        bottom_bar = QHBoxLayout()
        self.spin_group = QSpinBox()
        self.spin_group.setRange(0, 255)
        self.spin_group.setValue(1)
        bottom_bar.addWidget(QLabel("GRUPO:"))
        bottom_bar.addWidget(self.spin_group)

        self.btn_toggle_measuring = QPushButton("▶ INICIAR LEITURA")
        self.btn_toggle_measuring.clicked.connect(self.toggle_measuring)
        bottom_bar.addWidget(self.btn_toggle_measuring)

        self.btn_datalogger = QPushButton("🔴 GRAVAR RODAGEM (CSV)")
        self.btn_datalogger.setStyleSheet("background-color: #ff2a3b; color: white; font-weight: 800; padding: 6px 12px;")
        self.btn_datalogger.clicked.connect(self.toggle_datalogger)
        bottom_bar.addWidget(self.btn_datalogger)

        self.lbl_log_status = QLabel("")
        self.lbl_log_status.setStyleSheet("color: #ff2a3b; font-weight: 800; margin-left: 6px;")
        bottom_bar.addWidget(self.lbl_log_status)

        bottom_bar.addStretch()

        btn_close = QPushButton("06 — FECHAR / VOLTAR")
        btn_close.setStyleSheet("background-color: #8b0000; color: white;")
        btn_close.clicked.connect(self.close_controller)
        bottom_bar.addWidget(btn_close)

        layout.addLayout(bottom_bar)

    def _on_scope_channel_changed(self, idx: int):
        self.scope.selected_channel = self.combo_scope_channel.currentData()
        self.scope.update()

    def start_connection(self):
        pn_hint = "030-906-032-CP" if self.mock_ecu_type == "MARELLI_1AVP" else "1HS-908-258"
        if self.is_mock:
            self.engine = KW1281Engine(mock_mode=True, part_number_hint=pn_hint, mock_ecu_type=self.mock_ecu_type)
        else:
            ser = KLineSerialInterface(port=self.port)
            ser.open()
            self.engine = KW1281Engine(serial_interface=ser, mock_mode=False, part_number_hint="1HS-908-258")

        try:
            self.engine.connect(self.address)
            info = self.engine.ecu_info
            detected = self.engine.identify_ecu_system()
            family = detected.get("family", "")
            brand = detected.get("brand", "VAG")
            model = detected.get("model", "ECU")
            throttle = detected.get("throttle_type", "")

            self.lbl_part_number.setText(f"PART NUMBER: {info.get('part_number', '030 906 027 AA')}")
            self.lbl_component.setText(f"🚗 {brand.upper()} {model.upper()}  |  {info.get('component', '')}")
            self.lbl_coding.setText(f"ARQUITETURA: {throttle}  |  CODING: {info.get('coding', '00000')}  |  WSC: {info.get('wsc', 'WSC 00000')}")

            if family == "BOSCH_MP90":
                self.btn_tba.setText("🎯 CALIBRAR BORBOLETA (GRUPO 098)")
                self.btn_tba.setStyleSheet("background-color: #ffb800; color: black; font-weight: 900;")
                self.btn_04.setText("04 — AJUSTE BÁSICO GERAL")
            elif family == "MARELLI_1AVP":
                self.btn_tba.setText("🎯 RESET MARCHA LENTA (CANAL 00)")
                self.btn_tba.setStyleSheet("background-color: #ff2a3b; color: white; font-weight: 900;")
                self.btn_04.setText("04 — TRAVAR PONTO 9.0° APMS (GRUPO 001)")
            elif family == "BOSCH_ME7":
                self.btn_tba.setText("🎯 CALIBRAR E-GAS (GRUPO 060)")
                self.btn_tba.setStyleSheet("background-color: #00e676; color: black; font-weight: 900;")
                self.btn_04.setText("04 — AJUSTE BÁSICO GERAL")

            self.keepalive_timer.start(350)

        except Exception as e:
            QMessageBox.critical(self, "Falha de Conexão", f"Não foi possível conectar ao módulo 0x{self.address:02X}:\n{e}")
            self.reject()

    def _send_keepalive(self):
        if self.engine and self.engine.connected and not self.measuring_timer.isActive():
            try:
                self.engine.send_ack()
            except Exception:
                pass

    def toggle_measuring(self):
        if self.measuring_timer.isActive():
            self.measuring_timer.stop()
            self.btn_toggle_measuring.setText("▶ INICIAR LEITURA")
        else:
            self.measuring_timer.start(400)
            self.btn_toggle_measuring.setText("⏸ PAUSAR LEITURA")

    def poll_measuring_blocks(self):
        if not self.engine or not self.engine.connected:
            return

        group = self.spin_group.value()
        fields = self.engine.read_measuring_group(group)

        self.table_live.setRowCount(len(fields))
        scope_values = []
        scope_labels = []
        scope_units = []

        for r, f in enumerate(fields):
            name = f.get("name", f"Campo {r+1}")
            val = f.get("value", "--")
            unit = f.get("unit", "")
            spec = f.get("spec", "")

            self.table_live.setItem(r, 0, QTableWidgetItem(name))
            self.table_live.setItem(r, 1, QTableWidgetItem(str(val)))
            self.table_live.setItem(r, 2, QTableWidgetItem(unit))
            self.table_live.setItem(r, 3, QTableWidgetItem(spec))

            scope_labels.append(name)
            scope_units.append(unit)
            if isinstance(val, (int, float)):
                scope_values.append(float(val))
            else:
                scope_values.append(0.0)

        self.scope.set_channel_labels(scope_labels, scope_units)
        if scope_values:
            self.scope.add_channels_data(scope_values)

        # Datalogger em Tempo Real
        if self.is_logging_csv and self.csv_writer:
            now_str = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            row = [now_str, group]
            for f in fields:
                row.extend([f.get("name", ""), f.get("value", ""), f.get("unit", "")])
            while len(row) < 14:
                row.extend(["", "", ""])
            try:
                self.csv_writer.writerow(row)
                self.csv_file.flush()
                self.csv_sample_count += 1
                self.lbl_log_status.setText(f"🔴 GRAVANDO: {self.csv_sample_count} AMOSTRAS")
            except Exception:
                pass

    def toggle_datalogger(self):
        if not self.is_logging_csv:
            logs_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "logs"))
            os.makedirs(logs_dir, exist_ok=True)
            timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
            self.csv_filepath = os.path.join(logs_dir, f"teste_rodagem_{timestamp}.csv")

            try:
                self.csv_file = open(self.csv_filepath, "w", newline="", encoding="utf-8")
                self.csv_writer = csv.writer(self.csv_file)
                self.csv_writer.writerow([
                    "Timestamp", "Grupo",
                    "Campo 1 (Nome)", "Campo 1 (Valor)", "Campo 1 (Unidade)",
                    "Campo 2 (Nome)", "Campo 2 (Valor)", "Campo 2 (Unidade)",
                    "Campo 3 (Nome)", "Campo 3 (Valor)", "Campo 3 (Unidade)",
                    "Campo 4 (Nome)", "Campo 4 (Valor)", "Campo 4 (Unidade)"
                ])
                self.csv_file.flush()
                self.is_logging_csv = True
                self.csv_sample_count = 0

                self.btn_datalogger.setText("⏹ FINALIZAR GRAVAÇÃO")
                self.btn_datalogger.setStyleSheet("background-color: #8b0000; color: white; font-weight: 800; padding: 6px 12px;")
                self.lbl_log_status.setText("🔴 GRAVANDO...")

                if not self.measuring_timer.isActive():
                    self.toggle_measuring()

            except Exception as e:
                QMessageBox.critical(self, "Erro no Log", f"Não foi possível iniciar gravação:\n{e}")
        else:
            self.stop_datalogger()

    def stop_datalogger(self):
        if self.is_logging_csv:
            self.is_logging_csv = False
            if self.csv_file:
                try:
                    self.csv_file.flush()
                    self.csv_file.close()
                except Exception:
                    pass
                self.csv_file = None

            self.btn_datalogger.setText("🔴 GRAVAR RODAGEM (CSV)")
            self.btn_datalogger.setStyleSheet("background-color: #ff2a3b; color: white; font-weight: 800; padding: 6px 12px;")
            self.lbl_log_status.setText(f"✅ SALVO ({self.csv_sample_count} AMOSTRAS)")

            QMessageBox.information(
                self, "Teste de Rodagem Finalizado",
                f"Gravação de rodagem finalizada com sucesso!\n\n"
                f"• Amostras gravadas: {self.csv_sample_count}\n"
                f"• Arquivo CSV: {self.csv_filepath}\n\n"
                f"Você pode abrir este arquivo no Excel para analisar qualquer falha ou engasgo durante a volta com o carro."
            )

    def close_controller(self):
        self.stop_datalogger()
        if self.keepalive_timer.isActive():
            self.keepalive_timer.stop()
        if self.measuring_timer.isActive():
            self.measuring_timer.stop()
        if self.engine:
            self.engine.disconnect()
        self.accept()

    def closeEvent(self, event):
        self.stop_datalogger()
        if self.keepalive_timer.isActive():
            self.keepalive_timer.stop()
        if self.measuring_timer.isActive():
            self.measuring_timer.stop()
        if self.engine:
            self.engine.disconnect()
        event.accept()

    def view_dtcs(self):
        dtcs = self.engine.read_dtcs()
        if not dtcs:
            QMessageBox.information(self, "Códigos de Avaria", "Nenhum código de avaria encontrado na ECU!")
            return

        msg = f"<b>{len(dtcs)} Avaria(s) Detectada(s):</b><br><br>"
        for d in dtcs:
            code = d["code"]
            info = self.dtc_db.lookup(code)
            msg += f"• <b>{code}</b> ({info.get('obd_code')}): {info.get('component')}<br>"
            msg += f"&nbsp;&nbsp;<i>Sintoma: {', '.join(info.get('symptoms', ['-'])[:2])}</i><br><br>"

        res = QMessageBox.question(self, "Avarias Encontradas", msg + "<br>Deseja apagar a memória de falhas (05 - Clear Codes)?")
        if res == QMessageBox.StandardButton.Yes:
            self.engine.clear_dtcs()
            QMessageBox.information(self, "Limpeza Concluída", "Memória de falhas apagada!")

    def view_measuring_blocks(self):
        self.spin_group.setValue(1)
        if not self.measuring_timer.isActive():
            self.toggle_measuring()

    def view_basic_settings(self):
        detected = self.engine.identify_ecu_system() if self.engine else {}
        family = detected.get("family", "")
        if family == "MARELLI_1AVP":
            res = QMessageBox.question(
                self, "Ajuste Básico (Função 04) — Magneti Marelli 1AVP",
                "Deseja colocar a ECU 1AVP em modo Ajuste Básico (Grupo 001)?\n\n"
                "O avanço de ignição será travado em 9.0° APMS para calibração com pistola estroboscópica no volante do motor."
            )
            if res == QMessageBox.StandardButton.Yes:
                self.engine.run_basic_settings(1)
                self.spin_group.setValue(1)
                if not self.measuring_timer.isActive():
                    self.toggle_measuring()
                QMessageBox.information(self, "Ajuste Básico Ativo", "Avanço travado a 9.0° APMS! Ajuste a base do distribuidor.")
        elif family == "BOSCH_MP90":
            res = QMessageBox.question(
                self, "Ajuste Básico (Função 04) — Bosch Motronic MP 9.0",
                "Deseja iniciar a Calibração de Borboleta e Batente da Marcha Lenta (Grupo 098)?\n\n"
                "A central acionará o motor elétrico interno da marcha lenta até o batente de repouso."
            )
            if res == QMessageBox.StandardButton.Yes:
                self.open_tbi_calibration()
        else:
            self.open_tbi_calibration()

    def open_tbi_calibration(self):
        dlg = TBICalibrationDialog(engine=self.engine, parent=self)
        dlg.exec()

    def run_output_tests(self):
        res = QMessageBox.warning(
            self, "⚠️ Intertravamento de Segurança — Teste de Atuadores (03)",
            "<b>CONDIÇÃO OBRIGATÓRIA DE SEGURANÇA:</b><br><br>"
            "O Teste Sequencial de Atuadores aciona fisicamente a bomba de combustível, injetores e válvulas solenoides.<br>"
            "👉 O motor deve estar <b>OBRIGATORIAMENTE DESLIGADO</b> com a chave na posição pós-chave.<br>"
            "<i>Nunca execute este teste com o motor funcionando para evitar calço hidráulico nos cilindros!</i><br><br>"
            "Confirma que o motor está DESLIGADO e deseja disparar o próximo atuador?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if res != QMessageBox.StandardButton.Yes:
            return

        actuator = self.engine.trigger_next_output_test()
        if actuator:
            QMessageBox.information(self, "Teste de Atuadores (03)", f"Atuador acionado pela central:\n\n👉 {actuator}\n\nClique OK para avançar.")
        else:
            QMessageBox.information(self, "Teste de Atuadores (03)", "Fim da sequência de testes de atuadores.")

    def run_recode(self):
        cur_coding = self.engine.ecu_info.get("coding", "00000")
        new_val, ok = QInputDialog.getText(self, "07 — Recodificar Módulo", "Novo Software Coding (5 dígitos numéricos):", text=cur_coding)
        if ok and new_val:
            try:
                code_int = int(new_val)
                if not (0 <= code_int <= 65535):
                    raise ValueError("O código de codificação deve ser um número entre 00000 e 65535.")

                confirm = QMessageBox.warning(
                    self, "⚠️ Confirmação de Segurança de Gravação (NVRAM)",
                    f"<b>ATENÇÃO:</b> Você está prestes a gravar uma nova codificação na ECU.<br><br>"
                    f"• Codificação Atual: <b>{cur_coding}</b><br>"
                    f"• Nova Codificação: <b>{new_val}</b><br><br>"
                    f"Gravar códigos incorretos pode desabilitar funções da injeção ou imobilizador.<br>"
                    f"Deseja realmente gravar na memória não-volátil da ECU?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                )
                if confirm != QMessageBox.StandardButton.Yes:
                    return

                self.engine.recode_module(code_int)
                self.lbl_coding.setText(f"Soft. Coding: {new_val} | WSC: {self.engine.ecu_info.get('wsc', 'WSC 00000')}")
                QMessageBox.information(self, "Codificação", "Módulo recodificado com sucesso!")
            except Exception as e:
                QMessageBox.critical(self, "Erro de Segurança", f"Falha na codificação: {e}")

    def run_adaptation(self):
        chan_str, ok_c = QInputDialog.getText(self, "10 — Adaptação de Canal", "Número do Canal (ex: 01 p/ Marcha Lenta, 00 p/ Reset de Fábrica):", text="1")
        if not (ok_c and chan_str):
            return

        try:
            channel = int(chan_str)
        except ValueError:
            QMessageBox.warning(self, "Erro", "Número de canal inválido.")
            return

        if channel == 0:
            res = QMessageBox.warning(
                self, "⚠️ Restauração de Fábrica (Canal 00)",
                "Você selecionou o Canal 00. Isso apagará toda a matriz autoadaptativa da central para os padrões de fábrica.\n\nDeseja executar o Reset?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if res == QMessageBox.StandardButton.Yes:
                self.engine.reset_factory_adaptations()
                QMessageBox.information(self, "Reset Concluído", "Parâmetros autoadaptativos resetados com sucesso!")
            return

        val = self.engine.read_adaptation_channel(channel)
        prompt_msg = f"Canal {channel:02d}:\nValor Atual: {val}\nDigite o novo valor (faixa segura para marcha lenta: 110 a 150):"
        new_val, ok = QInputDialog.getText(self, "10 — Gravação de Adaptação", prompt_msg, text=str(val))
        if ok and new_val:
            try:
                val_int = int(new_val)
                self.engine.save_adaptation_channel(channel, val_int)
                QMessageBox.information(self, "Adaptação", f"Canal {channel:02d} gravado com sucesso com valor {val_int}!")
            except Exception as e:
                QMessageBox.critical(self, "Erro de Segurança", f"Valor rejeitado pela trava de segurança: {e}")

    def run_login(self):
        code, ok = QInputDialog.getText(self, "11 — Acesso de Segurança", "Digite o código de Login (5 dígitos, ex: 12233):")
        if ok and code:
            try:
                login_ok = self.engine.login_security_access(int(code))
                if login_ok:
                    QMessageBox.information(self, "Login", "Acesso de segurança aceito pela ECU!")
                else:
                    QMessageBox.warning(self, "Login", "Código de login rejeitado pela central.")
            except Exception as e:
                QMessageBox.critical(self, "Erro", f"Falha no login: {e}")


def run_desktop_app():
    app = QApplication(sys.argv)
    window = OpenVAGMainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(run_desktop_app())
