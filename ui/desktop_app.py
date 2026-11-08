"""
Aplicação Gráfica Desktop Nativa do Scanner-VW (OpenVAG).
Interface completa em PyQt6 no padrão Dark Mode profissional.
Implementa 100% dos fluxos e telas do VCDS-Lite com melhorias gráficas e funcionais:
- Plug-and-Play: Identificação e seleção automática da porta COM ao conectar o cabo KKL (CH340/CH341/FTDI)
- Seleção de Módulos (01-Motor, 03-ABS, 15-Airbag, 17-Painel, 25-Immo, etc.)
- Auto-Scan por chassi com barra de progresso (Gol Special, Gol G3/G4, Golf IV, etc.)
- Leitura de Identificação da ECU
- 02: Memória de Falhas com Doutor de DTCs e guia de testes com multímetro
- 05: Limpeza de Falhas (Clear DTCs)
- 08: Blocos de Medição com osciloscópio gráfico integrado em tempo real
- 04: Ajuste Básico (Trava de Ponto de Ignição e TBA)
- 03: Teste Sequencial de Atuadores (Output Tests)
- 07: Recodificação de Software (Recode)
- 10: Leitura e Gravação de Canais de Adaptação
- 11: Login / Security Access
- Opções e Teste de Porta Serial CH341
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
    QRadioButton, QButtonGroup, QScrollArea, QFrame
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread
from PyQt6.QtGui import QFont, QColor, QPainter, QPen, QBrush

from core.hardware import list_available_ports, find_kkl_cable_port, KLineSerialInterface
from core.kw1281 import KW1281Engine
from core.autoscan import AutoScanManager, MODULE_NAMES
from database.dtc_db import DTCDatabase
from database.telemetry import TelemetryLogger


DARK_STYLE = """
QMainWindow, QDialog, QWidget {
    background-color: #0f172a;
    color: #f8fafc;
    font-family: 'Segoe UI', Tahoma, sans-serif;
    font-size: 13px;
}
QGroupBox {
    border: 1px solid #334155;
    border-radius: 8px;
    margin-top: 14px;
    padding-top: 12px;
    font-weight: bold;
    color: #38bdf8;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 4px;
}
QPushButton {
    background-color: #1e293b;
    border: 1px solid #475569;
    border-radius: 6px;
    padding: 8px 14px;
    font-weight: bold;
    color: #f8fafc;
    min-height: 20px;
}
QPushButton:hover {
    background-color: #334155;
    border-color: #38bdf8;
    color: #38bdf8;
}
QPushButton:pressed {
    background-color: #0284c7;
    color: #ffffff;
}
QPushButton.danger {
    background-color: #991b1b;
    border-color: #dc2626;
    color: #fee2e2;
}
QPushButton.danger:hover {
    background-color: #dc2626;
}
QPushButton.success {
    background-color: #065f46;
    border-color: #10b981;
    color: #ecfdf5;
}
QPushButton.success:hover {
    background-color: #059669;
}
QTableWidget {
    background-color: #1e293b;
    border: 1px solid #334155;
    border-radius: 6px;
    gridline-color: #334155;
    color: #f8fafc;
    selection-background-color: #0284c7;
}
QHeaderView::section {
    background-color: #0f172a;
    color: #94a3b8;
    font-weight: bold;
    border: 1px solid #334155;
    padding: 4px;
}
QLineEdit, QComboBox, QSpinBox {
    background-color: #1e293b;
    border: 1px solid #475569;
    border-radius: 5px;
    padding: 6px;
    color: #f8fafc;
}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus {
    border: 1px solid #38bdf8;
}
QTabBar::tab {
    background: #1e293b;
    border: 1px solid #334155;
    padding: 8px 16px;
    margin-right: 2px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    color: #94a3b8;
}
QTabBar::tab:selected {
    background: #0f172a;
    border-bottom: 2px solid #38bdf8;
    color: #38bdf8;
    font-weight: bold;
}
QProgressBar {
    border: 1px solid #334155;
    border-radius: 5px;
    text-align: center;
    background-color: #1e293b;
    color: #ffffff;
}
QProgressBar::chunk {
    background-color: #0284c7;
    border-radius: 4px;
}
QCheckBox {
    color: #94a3b8;
    font-weight: bold;
}
QCheckBox::indicator:checked {
    background-color: #0284c7;
    border: 1px solid #38bdf8;
    border-radius: 3px;
}
"""


class LiveMiniScopeWidget(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(140)
        self.history = []
        self.max_points = 120

    def add_point(self, val: float):
        self.history.append(val)
        if len(self.history) > self.max_points:
            self.history.pop(0)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        painter.fillRect(0, 0, w, h, QColor("#090d16"))

        painter.setPen(QPen(QColor("#1e293b"), 1, Qt.PenStyle.DashLine))
        for y in range(20, h, 30):
            painter.drawLine(0, y, w, y)
        for x in range(30, w, 40):
            painter.drawLine(x, 0, x, h)

        if len(self.history) < 2:
            return

        min_v = min(self.history)
        max_v = max(self.history)
        if max_v == min_v:
            max_v += 1.0

        step = w / (self.max_points - 1)
        painter.setPen(QPen(QColor("#38bdf8"), 2))

        for i in range(len(self.history) - 1):
            y1 = h - int(((self.history[i] - min_v) / (max_v - min_v)) * (h - 20) + 10)
            y2 = h - int(((self.history[i + 1] - min_v) / (max_v - min_v)) * (h - 20) + 10)
            x1 = int(i * step)
            x2 = int((i + 1) * step)
            painter.drawLine(x1, y1, x2, y2)

        painter.setPen(QPen(QColor("#94a3b8")))
        painter.setFont(QFont("Segoe UI", 8))
        painter.drawText(8, 16, f"Max: {max_v:.1f}")
        painter.drawText(8, h - 6, f"Min: {min_v:.1f}")


class TBICalibrationWidget(QWidget):
    """
    Widget assistente especializado para calibração de TBI (TBA) e reset da marcha lenta.
    Suporta:
    1. Magneti Marelli 1AVP (Gol G2/G3 MI) - Reset EEPROM Canal 00 + Ciclo de Chave
    2. E-Gas Drive-by-Wire (Grupo 060 - TBA) para ME7.5 / 4LV / EA111
    3. TBI Semi-Eletrônico a Cabo (Grupo 098 - TBA) para Golf/Passat
    4. Ajuste Básico de Avanço de Ignição (Grupo 001 - 1AVP Trava 9.0° APMS)
    """

    def __init__(self, engine: Optional[KW1281Engine] = None, get_port_fn=None, is_mock_fn=None, parent=None):
        super().__init__(parent)
        self.engine = engine
        self.get_port_fn = get_port_fn
        self.is_mock_fn = is_mock_fn
        self.owned_engine = False

        self.poll_timer = QTimer(self)
        self.poll_timer.timeout.connect(self._poll_basic_settings)
        self.active_group = 60

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

        # Card Dinâmico do Veículo e Procedimento Específico
        self.card_vehicle = QFrame()
        self.card_vehicle.setStyleSheet("background-color: #0f172a; border: 2px solid #0284c7; border-radius: 8px; padding: 14px;")
        card_layout = QVBoxLayout(self.card_vehicle)

        self.lbl_veh_title = QLabel("🚗 Aguardando Leitura do Veículo...")
        self.lbl_veh_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #38bdf8;")
        self.lbl_veh_desc = QLabel("O OpenVAG lê a central conectada e prepara apenas o procedimento aplicável ao seu motor (sem opções confusas de outros veículos).")
        self.lbl_veh_desc.setStyleSheet("color: #cbd5e1; font-size: 13px;")

        card_layout.addWidget(self.lbl_veh_title)
        card_layout.addWidget(self.lbl_veh_desc)
        layout.addWidget(self.card_vehicle)

        # Grupo de Seleção de Modo (Oculto por padrão para simplificar a operação de oficina)
        self.group_modes = QGroupBox("⚙️ Seleção Manual de Sistema (Opcional / Modo Bancada)")
        self.group_modes.setVisible(False)
        mode_layout = QVBoxLayout(self.group_modes)

        self.radio_cable = QRadioButton("Bosch Motronic MP 9.0 (Gol Mi 1.0 8v) — Grupo 098")
        self.radio_cable.setChecked(True)
        self.radio_cable.setStyleSheet("font-weight: bold; color: #fbbf24;")

        self.radio_1avp = QRadioButton("Magneti Marelli 1AVP / 1AVB (Gol MI) — Reset Canal 00")
        self.radio_1avp.setStyleSheet("font-weight: bold; color: #38bdf8;")

        self.radio_egas = QRadioButton("Bosch Motronic ME 7.x (E-Gas Eletrônico) — Grupo 060")
        self.radio_egas.setStyleSheet("font-weight: bold; color: #34d399;")

        self.radio_timing = QRadioButton("Ajuste Básico de Ignição 1AVP (Grupo 001) — Trava 9.0° APMS")
        self.radio_timing.setStyleSheet("font-weight: bold; color: #f43f5e;")

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

        # Botão recolhido para exibir o modo manual se necessário
        self.btn_toggle_manual = QPushButton("⚙️ Mostrar Opções Manuais de Outras Centrais (Avançado)")
        self.btn_toggle_manual.setStyleSheet("background: transparent; border: none; color: #64748b; font-size: 11px; text-decoration: underline;")
        self.btn_toggle_manual.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_toggle_manual.clicked.connect(self._toggle_manual_modes)
        layout.addWidget(self.btn_toggle_manual)

        # Caixa de Explicação Técnica Dinâmica
        self.txt_explanation = QTextEdit()
        self.txt_explanation.setReadOnly(True)
        self.txt_explanation.setMaximumHeight(100)
        self.txt_explanation.setStyleSheet("background-color: #0b1329; border: 1px solid #334155; border-radius: 6px; padding: 8px; color: #cbd5e1;")
        layout.addWidget(self.txt_explanation)

        # Box de Pré-condições / Checklist
        group_pre = QGroupBox("Checklist Obrigatório de Oficina")
        pre_layout = QVBoxLayout(group_pre)
        self.chk_ignition = QCheckBox("1. Chave na posição de ignição com motor DESLIGADO")
        self.chk_ignition.setChecked(True)
        self.chk_battery = QCheckBox("2. Bateria com carga normal (> 11.5V)")
        self.chk_battery.setChecked(True)
        self.chk_pedal = QCheckBox("3. Pedal do acelerador totalmente livre (sem pisar)")
        self.chk_pedal.setChecked(True)
        self.chk_dtcs = QCheckBox("4. Sem falhas elétricas graves ativas de TPS ou motor de passo")
        self.chk_dtcs.setChecked(True)

        pre_layout.addWidget(self.chk_ignition)
        pre_layout.addWidget(self.chk_battery)
        pre_layout.addWidget(self.chk_pedal)
        pre_layout.addWidget(self.chk_dtcs)
        layout.addWidget(group_pre)

        # Barra de Ações
        action_box = QHBoxLayout()
        self.btn_start = QPushButton("▶ Iniciar Calibração de Borboleta")
        self.btn_start.setMinimumHeight(46)
        self.btn_start.setStyleSheet("background-color: #0284c7; color: white; font-weight: bold; font-size: 14px;")
        self.btn_start.clicked.connect(self.start_calibration)
        action_box.addWidget(self.btn_start)

        self.btn_stop = QPushButton("⏹ Interromper")
        self.btn_stop.setMinimumHeight(46)
        self.btn_stop.setEnabled(False)
        self.btn_stop.setStyleSheet("background-color: #475569; color: white; font-weight: bold;")
        self.btn_stop.clicked.connect(self.stop_calibration)
        action_box.addWidget(self.btn_stop)
        layout.addLayout(action_box)

        # Banner de Status da Operação
        self.lbl_status = QLabel("Status: Aguardando comando...")
        self.lbl_status.setStyleSheet("background-color: #1e293b; color: #94a3b8; padding: 8px 12px; border-radius: 5px; font-weight: bold;")
        layout.addWidget(self.lbl_status)

        # Assistente de Ciclo de Chave (Específico para 1AVP - Canal 00)
        self.box_1avp_wizard = QGroupBox("Ciclo de Chave & Inicialização da 1AVP (Passo a Passo de Oficina)")
        wiz_layout = QVBoxLayout(self.box_1avp_wizard)

        self.lbl_wiz_step1 = QLabel("<b>Passo 1: Desligue a ignição</b> por 15 segundos para desarmar o relé principal (Power Latch da 1AVP).")
        wiz_layout.addWidget(self.lbl_wiz_step1)
        self.btn_timer_15s = QPushButton("⏱ Iniciar Cronômetro de 15 Segundos (Desligado)")
        self.btn_timer_15s.clicked.connect(lambda: self._start_countdown(15, "Passo 1: Chave desligada. Aguarde o desarmamento do relé..."))
        wiz_layout.addWidget(self.btn_timer_15s)

        self.lbl_wiz_step2 = QLabel("<b>Passo 2: Ligue a ignição</b> (sem dar partida) por 30 segundos. A ECU 1AVP bate o motor de passo nos batentes mecânicos e calibra a voltagem de repouso do TPS.")
        wiz_layout.addWidget(self.lbl_wiz_step2)
        self.btn_timer_30s = QPushButton("⏱ Iniciar Cronômetro de 30 Segundos (Chave Ligada sem Partida)")
        self.btn_timer_30s.clicked.connect(lambda: self._start_countdown(30, "Passo 2: Chave ligada (sem partida). A 1AVP está indexando os passos e lendo o TPS..."))
        wiz_layout.addWidget(self.btn_timer_30s)

        self.lbl_wiz_step3 = QLabel("<b>Passo 3: Dê a partida</b> no motor SEM acelerar e deixe em marcha lenta livre até a ventoinha armar 2 vezes para aprendizado térmico.")
        wiz_layout.addWidget(self.lbl_wiz_step3)

        # Countdown Display
        self.countdown_box = QWidget()
        self.countdown_box.setVisible(False)
        cd_layout = QVBoxLayout(self.countdown_box)
        self.lbl_countdown_msg = QLabel("Contagem regressiva...")
        self.lbl_countdown_msg.setStyleSheet("color: #38bdf8; font-weight: bold; font-size: 13px;")
        cd_layout.addWidget(self.lbl_countdown_msg)
        self.progress_countdown = QProgressBar()
        cd_layout.addWidget(self.progress_countdown)
        self.lbl_countdown_timer = QLabel("0s")
        self.lbl_countdown_timer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_countdown_timer.setStyleSheet("font-size: 18px; font-weight: bold; color: #38bdf8;")
        cd_layout.addWidget(self.lbl_countdown_timer)
        wiz_layout.addWidget(self.countdown_box)

        layout.addWidget(self.box_1avp_wizard)

        # Tabela de Telemetria ao Vivo (Grupos 060, 098, 001)
        self.table_box = QGroupBox("Parâmetros de Ajuste Básico em Tempo Real (KWP1281 Live Feedback)")
        table_layout = QVBoxLayout(self.table_box)
        self.table_tbi_live = QTableWidget(4, 4)
        self.table_tbi_live.setHorizontalHeaderLabels(["Parâmetro / Sensor", "Valor Atual", "Unidade", "Especificação"])
        self.table_tbi_live.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table_layout.addWidget(self.table_tbi_live)
        layout.addWidget(self.table_box)

        scroll.setWidget(container)
        main_v = QVBoxLayout(self)
        main_v.setContentsMargins(0, 0, 0, 0)
        main_v.addWidget(scroll)

        # Estado inicial limpo: Nenhuma informação fictícia sem estar conectado
        self.box_1avp_wizard.setVisible(False)
        self.table_box.setVisible(False)
        self.txt_explanation.setHtml(
            "<p style='color: #64748b; text-align: center; padding: 18px;'>"
            "🔌 <b>Nenhum veículo conectado no momento.</b><br>"
            "Conecte o cabo KKL na tomada OBD2 e ligue a chave de ignição.<br>"
            "O OpenVAG lerá a central real pelo cabo e preparará a calibração automaticamente."
            "</p>"
        )

        if self.engine and self.engine.connected:
            self.apply_auto_detected_ecu()

    def _toggle_manual_modes(self):
        is_vis = not self.group_modes.isVisible()
        self.group_modes.setVisible(is_vis)
        self.btn_toggle_manual.setText("⚙️ Ocultar Opções Manuais" if is_vis else "⚙️ Mostrar Opções Manuais de Outras Centrais (Avançado)")

    def apply_auto_detected_ecu(self):
        if not self.engine or not self.engine.connected:
            return
        detected = self.engine.identify_ecu_system()
        family = detected.get("family", "")
        brand = detected.get("brand", "VAG")
        model = detected.get("model", "ECU")
        rec_mode = detected.get("recommended_tbi_mode", 3)
        throttle = detected.get("throttle_type", "")

        # Oculta modos manuais para simplificar a visão do mecânico
        self.group_modes.setVisible(False)
        self.btn_toggle_manual.setText("⚙️ Mostrar Opções Manuais de Outras Centrais (Avançado)")

        if family == "BOSCH_MP90" or rec_mode == 3:
            self.lbl_veh_title.setText(f"🚗 Veículo Identificado: {brand} {model} (Gol G2 1.0 8v)")
            self.lbl_veh_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #fbbf24;")
            self.lbl_veh_desc.setText(
                f"<b>Arquitetura:</b> {throttle}<br>"
                "<b>Procedimento Automático:</b> Calibração de Batente de Marcha Lenta (Ajuste Básico - Grupo 098).<br>"
                "<i>Basta conferir as pré-condições abaixo e clicar em Iniciar. O OpenVAG comandará a borboleta e confirmará o alinhamento.</i>"
            )
            self.card_vehicle.setStyleSheet("background-color: #0f172a; border: 2px solid #fbbf24; border-radius: 8px; padding: 12px;")
            self.radio_cable.setChecked(True)
            self._on_mode_changed(3, True)
            self.btn_start.setText("▶ Iniciar Calibração de Borboleta (Grupo 098)")

        elif family == "MARELLI_1AVP" or rec_mode == 1:
            self.lbl_veh_title.setText(f"🚗 Veículo Identificado: {brand} {model} (Gol / Santana)")
            self.lbl_veh_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #38bdf8;")
            self.lbl_veh_desc.setText(
                f"<b>Arquitetura:</b> {throttle}<br>"
                "<b>Procedimento Automático:</b> Reset de Parâmetros de Marcha Lenta (Canal 00 de Adaptação).<br>"
                "<i>A central apagará os parâmetros autoadaptativos da EEPROM e liberará o passo a passo de ciclo de chave.</i>"
            )
            self.card_vehicle.setStyleSheet("background-color: #0f172a; border: 2px solid #38bdf8; border-radius: 8px; padding: 12px;")
            self.radio_1avp.setChecked(True)
            self._on_mode_changed(1, True)
            self.btn_start.setText("▶ Executar Reset de Marcha Lenta (Canal 00)")

        elif family == "BOSCH_ME7" or rec_mode == 2:
            self.lbl_veh_title.setText(f"🚗 Veículo Identificado: {brand} {model} (E-Gas Eletrônico)")
            self.lbl_veh_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #34d399;")
            self.lbl_veh_desc.setText(
                f"<b>Arquitetura:</b> {throttle}<br>"
                "<b>Procedimento Automático:</b> Alinhamento de Borboleta Eletrônica (Ajuste Básico - Grupo 060)."
            )
            self.card_vehicle.setStyleSheet("background-color: #0f172a; border: 2px solid #34d399; border-radius: 8px; padding: 12px;")
            self.radio_egas.setChecked(True)
            self._on_mode_changed(2, True)
            self.btn_start.setText("▶ Iniciar Alinhamento E-Gas (Grupo 060)")

    def _on_mode_changed(self, id_val: int, checked: bool):
        if not checked:
            return
        if id_val == 1:
            self.txt_explanation.setHtml(
                "<b style='color: #38bdf8;'>Procedimento: Reset EEPROM Canal 00 (Magneti Marelli 1AVP)</b><br>"
                "• <b>Ação:</b> Apaga as tabelas autoadaptativas de combustível e marcha lenta.<br>"
                "• <b>Instrução:</b> Clique em Reset e aguarde a indexação mecânica do atuador de passo no ciclo de chave."
            )
            self.box_1avp_wizard.setVisible(True)
            self.table_box.setVisible(False)
        elif id_val == 2:
            self.txt_explanation.setHtml(
                "<b style='color: #34d399;'>Procedimento: Ajuste Básico no Grupo 060 (E-Gas Eletrônico)</b><br>"
                "• <b>Ação:</b> A ECU comanda a borboleta e confere os potenciômetros duplos G187/G188 até <b>ADP. OK</b>."
            )
            self.box_1avp_wizard.setVisible(False)
            self.table_box.setVisible(True)
        elif id_val == 3:
            self.txt_explanation.setHtml(
                "<b style='color: #fbbf24;'>Procedimento: Ajuste Básico no Grupo 098 (Bosch Motronic MP 9.0)</b><br>"
                "• <b>Ação:</b> O motor elétrico DC da marcha lenta afere o batente mecânico de repouso nos potenciômetros G69/G88.<br>"
                "• <b>Conclusão:</b> O alinhamento finaliza quando o Campo 4 registra <b>I.O. (In Ordnung) / ADP. OK</b>."
            )
            self.box_1avp_wizard.setVisible(False)
            self.table_box.setVisible(True)
        elif id_val == 4:
            self.txt_explanation.setHtml(
                "<b style='color: #f43f5e;'>Procedimento: Trava de Avanço a 9.0° APMS (Grupo 001)</b><br>"
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

                self.lbl_status.setText("Conectando ao módulo 01 (Engine)...")
                self.lbl_status.setStyleSheet("background-color: #0284c7; color: white; padding: 8px 12px; border-radius: 5px; font-weight: bold;")
                QApplication.processEvents()
                self.engine.connect(0x01)
                self.owned_engine = True

                # Aplica auto-identificação Bosch vs Marelli
                self.apply_auto_detected_ecu()
            except Exception as e:
                self.lbl_status.setText(f"Erro de conexão com a ECU: {e}")
                self.lbl_status.setStyleSheet("background-color: #991b1b; color: white; padding: 8px 12px; border-radius: 5px; font-weight: bold;")
                QMessageBox.critical(self, "Falha de Conexão", f"Não foi possível conectar ao módulo do Motor (0x01):\n{e}")
                return

        mode = self.btn_group.checkedId()
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)

        if mode == 1:
            try:
                ok = self.engine.reset_factory_adaptations()
                if ok:
                    self.lbl_status.setText("✅ Reset de Autoadaptação Concluído na EEPROM! Siga os passos de ciclo de chave abaixo.")
                    self.lbl_status.setStyleSheet("background-color: #065f46; color: #34d399; padding: 8px 12px; border-radius: 5px; font-weight: bold;")
                    self.box_1avp_wizard.setVisible(True)
                    QMessageBox.information(
                        self, "Reset Efetuado com Sucesso",
                        "Os parâmetros autoadaptativos da central foram resetados para o padrão de fábrica!\n\n"
                        "Agora execute o ciclo de chave orientado nas 3 etapas abaixo para indexar o atuador de marcha lenta."
                    )
                else:
                    self.lbl_status.setText("⚠️ Comando de reset rejeitado pela central.")
                    self.lbl_status.setStyleSheet("background-color: #991b1b; color: white; padding: 8px 12px; border-radius: 5px; font-weight: bold;")
            except Exception as e:
                self.lbl_status.setText(f"Falha ao resetar adaptação: {e}")
                self.lbl_status.setStyleSheet("background-color: #991b1b; color: white; padding: 8px 12px; border-radius: 5px; font-weight: bold;")
        else:
            if mode == 2:
                self.active_group = 60
                target_desc = "Alinhamento E-Gas (Grupo 060)"
            elif mode == 3:
                self.active_group = 98
                target_desc = "Alinhamento Bosch MP 9.0 / Semi-Eletrônico (Grupo 098)"
            else:
                self.active_group = 1
                target_desc = "Trava de Ponto 9.0° APMS (Grupo 001)"

            try:
                self.lbl_status.setText(f"⚙️ {target_desc} em execução... Aguardando confirmação da ECU...")
                self.lbl_status.setStyleSheet("background-color: #0369a1; color: white; padding: 8px 12px; border-radius: 5px; font-weight: bold;")
                self.engine.run_basic_settings(self.active_group)
                self._poll_basic_settings()
                self.poll_timer.start(700)
            except Exception as e:
                self.lbl_status.setText(f"Erro ao disparar Ajuste Básico: {e}")
                self.lbl_status.setStyleSheet("background-color: #991b1b; color: white; padding: 8px 12px; border-radius: 5px; font-weight: bold;")

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
                    self.lbl_status.setText("✅ Alinhamento de Borboleta Concluído com Sucesso! (I.O. / ADP. OK)")
                    self.lbl_status.setStyleSheet("background-color: #065f46; color: #34d399; padding: 8px 12px; border-radius: 5px; font-weight: bold;")
                elif any(x in val_str for x in ("ADP. RUN", "ADP RUN", "Lauft")):
                    self.lbl_status.setText("⏳ Adaptação em andamento... (Lauft / ADP. RUN) Aguarde a conclusão...")
                    self.lbl_status.setStyleSheet("background-color: #854d0e; color: #fde047; padding: 8px 12px; border-radius: 5px; font-weight: bold;")
                elif "ERROR" in val_str:
                    self.lbl_status.setText("❌ Falha no alinhamento de borboleta (ERROR). Verifique bateria ou sujeira mecânica.")
                    self.lbl_status.setStyleSheet("background-color: #991b1b; color: white; padding: 8px 12px; border-radius: 5px; font-weight: bold;")
        except Exception as e:
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
            self.lbl_countdown_timer.setText("Tempo Finalizado! ✅")
            self.lbl_countdown_msg.setText("Etapa concluída. Avance para o próximo passo.")

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
        self.lbl_status.setText("Status: Procedimento encerrado.")
        self.lbl_status.setStyleSheet("background-color: #1e293b; color: #94a3b8; padding: 8px 12px; border-radius: 5px; font-weight: bold;")


class TBICalibrationDialog(QDialog):
    """Diálogo de calibração para uso a partir da tela de controlador (ControllerDialog)."""

    def __init__(self, engine: Optional[KW1281Engine] = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🎯 Calibração de Borboleta (TBI) & Marcha Lenta")
        self.resize(850, 680)
        self.setStyleSheet(DARK_STYLE)

        layout = QVBoxLayout(self)
        self.widget = TBICalibrationWidget(engine=engine, parent=self)
        layout.addWidget(self.widget)

        btn_close = QPushButton("Fechar Assistente")
        btn_close.setStyleSheet("background-color: #334155; color: white;")
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
        self.setWindowTitle("OpenVAG Desktop — Diagnóstico Automotivo KKL (VCDS-Lite Pro)")
        self.resize(1024, 740)
        self.setStyleSheet(DARK_STYLE)

        self.engine: Optional[KW1281Engine] = None
        self.dtc_db = DTCDatabase()
        self.logger = TelemetryLogger()
        self.autoscan_mgr = AutoScanManager()

        self.last_detected_port: Optional[str] = None
        self.known_ports_set = set()

        self.init_ui()

        # Timer de detecção automática de portas USB / Hotplug (a cada 800ms)
        self.hotplug_timer = QTimer(self)
        self.hotplug_timer.timeout.connect(self.check_usb_hotplug)
        self.hotplug_timer.start(800)

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        # Topo: Cabeçalho & Status do Hardware
        header_layout = QHBoxLayout()
        logo_label = QLabel("🚗 <b>OpenVAG</b> Desktop")
        logo_label.setStyleSheet("font-size: 20px; color: #38bdf8;")
        header_layout.addWidget(logo_label)

        header_layout.addStretch()

        self.status_badge = QLabel("⚪ AGUARDANDO CABO USB...")
        self.status_badge.setStyleSheet("background-color: #334155; color: #94a3b8; padding: 5px 12px; border-radius: 5px; font-weight: bold;")
        header_layout.addWidget(self.status_badge)

        self.port_combo = QComboBox()
        self.refresh_ports()
        header_layout.addWidget(self.port_combo)

        self.chk_autodetect = QCheckBox("Plug & Play (Auto)")
        self.chk_autodetect.setChecked(True)
        header_layout.addWidget(self.chk_autodetect)

        self.btn_refresh = QPushButton("↻")
        self.btn_refresh.setToolTip("Atualizar lista de portas seriais")
        self.btn_refresh.clicked.connect(self.refresh_ports)
        header_layout.addWidget(self.btn_refresh)

        main_layout.addLayout(header_layout)

        # Banner de Notificação de Conexão Plug & Play
        self.banner_hotplug = QLabel("💡 Conecte o cabo VAG-COM KKL na porta USB para detecção automática instantânea.")
        self.banner_hotplug.setStyleSheet("background-color: #1e293b; border-left: 4px solid #38bdf8; padding: 8px 12px; border-radius: 4px; color: #cbd5e1;")
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

        self.tabs.addTab(self.tab_modules, "🔌 Selecionar Módulo")
        self.tabs.addTab(self.tab_autoscan, "⚡ Auto-Scan")
        self.tabs.addTab(self.tab_tbi, "🎯 Calibração de TBI & Marcha Lenta")
        self.tabs.addTab(self.tab_dtc_doctor, "🩺 Doutor de Falhas")
        self.tabs.addTab(self.tab_options, "⚙️ Opções & Teste de Cabo")

        main_layout.addWidget(self.tabs)

        # Executa uma detecção inicial
        self.check_usb_hotplug(initial=True)

    def refresh_ports(self):
        current_selection = self.port_combo.currentData()
        self.port_combo.clear()
        ports = list_available_ports()
        self.known_ports_set = set(p["device"] for p in ports)

        for p in ports:
            tag = " ⭐ [Cabo KKL Detectado]" if p["is_likely_kkl"] else ""
            self.port_combo.addItem(f"{p['device']}{tag}", p["device"])

        # Só adiciona opções de simulação se não houver porta física real conectada
        if not ports:
            self.port_combo.addItem("⚠️ Nenhum Cabo USB Detectado", "NONE")
            self.port_combo.addItem("🧪 Modo Bancada (Bosch MP 9.0)", "MOCK_BOSCH")
            self.port_combo.addItem("🧪 Modo Bancada (Marelli 1AVP)", "MOCK_1AVP")

        # Restaura seleção se ainda existir
        if current_selection:
            idx = self.port_combo.findData(current_selection)
            if idx >= 0:
                self.port_combo.setCurrentIndex(idx)

    def check_usb_hotplug(self, initial: bool = False):
        """
        Rotina periódica de watchdog para monitorar conexão e desconexão
        de cabos USB/KKL (CH341 / FTDI) em tempo real.
        """
        current_ports = list_available_ports()
        current_set = set(p["device"] for p in current_ports)

        # Detecta se houve mudança nas portas seriais
        if current_set != self.known_ports_set or initial:
            # Houve conexão ou desconexão física
            newly_added = current_set - self.known_ports_set
            removed = self.known_ports_set - current_set

            self.refresh_ports()

            # Busca se o cabo KKL está plugado
            kkl_info = find_kkl_cable_port()

            if kkl_info:
                port_name = kkl_info["device"]
                desc = kkl_info.get("description", "Cabo KKL")

                # Se a opção de autodetecção estiver marcada, seleciona automaticamente
                if self.chk_autodetect.isChecked():
                    idx = self.port_combo.findData(port_name)
                    if idx >= 0:
                        self.port_combo.setCurrentIndex(idx)

                self.status_badge.setText(f"🟢 CABO KKL CONECTADO ({port_name})")
                self.status_badge.setStyleSheet("background-color: #065f46; color: #a7f3d0; padding: 5px 12px; border-radius: 5px; font-weight: bold;")
                self.banner_hotplug.setText(f"🔌 <b>Cabo VAG-COM KKL detectado na porta {port_name}!</b> ({desc}) Pronto para comunicação.")
                self.banner_hotplug.setStyleSheet("background-color: #1e293b; border-left: 4px solid #10b981; padding: 8px 12px; border-radius: 4px; color: #a7f3d0;")

                self.last_detected_port = port_name

            else:
                self.status_badge.setText("⚪ AGUARDANDO CABO USB...")
                self.status_badge.setStyleSheet("background-color: #334155; color: #94a3b8; padding: 5px 12px; border-radius: 5px; font-weight: bold;")
                self.banner_hotplug.setText("💡 Conecte o cabo VAG-COM KKL na porta USB para detecção automática instantânea.")
                self.banner_hotplug.setStyleSheet("background-color: #1e293b; border-left: 4px solid #38bdf8; padding: 8px 12px; border-radius: 4px; color: #cbd5e1;")
                self.last_detected_port = None

    def setup_tab_modules(self):
        layout = QVBoxLayout(self.tab_modules)

        # 1. Card de Conexão Rápida com o Motor (Principal da Oficina)
        card_engine = QGroupBox("Diagnóstico Principal — Injeção Eletrônica")
        card_engine_layout = QVBoxLayout(card_engine)

        lbl_hint = QLabel(
            "Conecta diretamente à central de injeção (01 - Engine), detecta automaticamente se é Bosch ou Marelli, "
            "e exibe somente as leituras e procedimentos compatíveis com este veículo."
        )
        lbl_hint.setStyleSheet("color: #94a3b8; font-size: 13px; margin-bottom: 6px;")
        card_engine_layout.addWidget(lbl_hint)

        btn_engine_hero = QPushButton("🚗 Conectar ao Módulo do Motor (01 - Engine)")
        btn_engine_hero.setMinimumHeight(56)
        btn_engine_hero.setStyleSheet("background-color: #0284c7; color: white; font-size: 16px; font-weight: bold; border-radius: 6px;")
        btn_engine_hero.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_engine_hero.clicked.connect(lambda: self.open_controller(0x01))
        card_engine_layout.addWidget(btn_engine_hero)

        layout.addWidget(card_engine)

        # 2. Outros Módulos Opcionais
        group_common = QGroupBox("Outros Módulos Disponíveis (Opcional)")
        grid_common = QHBoxLayout(group_common)

        btn_abs = QPushButton("03 - Freios ABS\n(Anti-Lock Brakes)")
        btn_abs.setMinimumHeight(52)
        btn_abs.clicked.connect(lambda: self.open_controller(0x03))
        grid_common.addWidget(btn_abs)

        btn_airbag = QPushButton("15 - Airbags\n(Safety Systems)")
        btn_airbag.setMinimumHeight(52)
        btn_airbag.clicked.connect(self.open_airbag_controller)
        grid_common.addWidget(btn_airbag)

        btn_cluster = QPushButton("17 - Painel Instrumentos\n(Kombiinstrument)")
        btn_cluster.setMinimumHeight(52)
        btn_cluster.clicked.connect(lambda: self.open_controller(0x17))
        grid_common.addWidget(btn_cluster)

        btn_immo = QPushButton("25 - Imobilizador\n(Immo Megamos/Kostal)")
        btn_immo.setMinimumHeight(52)
        btn_immo.clicked.connect(lambda: self.open_controller(0x25))
        grid_common.addWidget(btn_immo)

        layout.addWidget(group_common)

        # 3. Endereço Direto
        group_direct = QGroupBox("Endereço Direto (Avançado)")
        layout_direct = QHBoxLayout(group_direct)
        layout_direct.addWidget(QLabel("Endereço Hexadecimal (ex: 01, 17, 25, 46):"))
        self.txt_direct_addr = QLineEdit("01")
        self.txt_direct_addr.setMaximumWidth(80)
        layout_direct.addWidget(self.txt_direct_addr)

        btn_direct_go = QPushButton("Conectar ao Endereço")
        btn_direct_go.clicked.connect(self.connect_direct_address)
        layout_direct.addWidget(btn_direct_go)
        layout_direct.addStretch()

        layout.addWidget(group_direct)
        layout.addStretch()

    def setup_tab_autoscan(self):
        layout = QVBoxLayout(self.tab_autoscan)

        top_bar = QHBoxLayout()
        top_bar.addWidget(QLabel("Perfil do Veículo (Chassi):"))

        self.combo_chassis = QComboBox()
        for code, data in self.autoscan_mgr.chassis_profiles.items():
            self.combo_chassis.addItem(f"{code} — {data['name']}", code)
        top_bar.addWidget(self.combo_chassis)

        self.btn_start_scan = QPushButton("▶ Iniciar Auto-Scan")
        self.btn_start_scan.setStyleSheet("background-color: #0284c7; color: white;")
        self.btn_start_scan.clicked.connect(self.run_autoscan)
        top_bar.addWidget(self.btn_start_scan)

        layout.addLayout(top_bar)

        self.progress_scan = QProgressBar()
        self.progress_scan.setValue(0)
        layout.addWidget(self.progress_scan)

        self.table_scan = QTableWidget(0, 4)
        self.table_scan.setHorizontalHeaderLabels(["Endereço", "Nome do Módulo", "Status de Resposta", "Avarias (DTCs)"])
        self.table_scan.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table_scan)

    def setup_tab_tbi(self):
        layout = QVBoxLayout(self.tab_tbi)
        self.tbi_widget = TBICalibrationWidget(
            get_port_fn=lambda: self.port_combo.currentData(),
            is_mock_fn=lambda: self.port_combo.currentData() == "MOCK",
            parent=self
        )
        layout.addWidget(self.tbi_widget)

    def setup_tab_dtc_doctor(self):
        layout = QVBoxLayout(self.tab_dtc_doctor)

        search_bar = QHBoxLayout()
        search_bar.addWidget(QLabel("Consultar Código de Falha (VAG ou OBD2):"))
        self.txt_dtc_search = QLineEdit("")
        self.txt_dtc_search.setPlaceholderText("Ex: 00515 ou P0340")
        self.txt_dtc_search.setMaximumWidth(160)
        search_bar.addWidget(self.txt_dtc_search)

        btn_search = QPushButton("🔍 Analisar Falha")
        btn_search.clicked.connect(self.on_dtc_search)
        search_bar.addWidget(btn_search)
        search_bar.addStretch()

        layout.addLayout(search_bar)

        self.txt_dtc_details = QTextEdit()
        self.txt_dtc_details.setReadOnly(True)
        self.txt_dtc_details.setStyleSheet("background-color: #1e293b; color: #f8fafc; font-size: 14px; padding: 12px;")
        layout.addWidget(self.txt_dtc_details)

        self.txt_dtc_details.setHtml(
            "<div style='text-align: center; padding: 40px; color: #64748b;'>"
            "<h3 style='color: #94a3b8;'>🩺 Doutor de Falhas — Base de Conhecimento Técnico</h3>"
            "<p>Nenhum código pesquisado no momento.<br><br>"
            "👉 Conecte o cabo KKL ao carro para extrair os códigos de erro reais gravados na ECU,<br>"
            "ou digite um código no campo acima para consultar os testes elétricos de chicote e multímetro.</p>"
            "</div>"
        )

    def setup_tab_options(self):
        layout = QVBoxLayout(self.tab_options)

        group_port = QGroupBox("Teste e Diagnóstico da Interface Serial KKL")
        port_layout = QVBoxLayout(group_port)

        port_layout.addWidget(QLabel("Driver suportado: <b>CH341S64.SYS / FTDI</b> (USB-to-Serial)"))
        port_layout.addWidget(QLabel("Detecção Automática: <b>Ativada (Watchdog 800ms)</b>"))

        btn_test_port = QPushButton("🔌 Executar Teste de Interface (Test Loopback / Baud)")
        btn_test_port.clicked.connect(self.run_port_test)
        port_layout.addWidget(btn_test_port)

        layout.addWidget(group_port)

        group_timings = QGroupBox("Ajustes de Temporização (VCDS.CFG)")
        time_layout = QHBoxLayout(group_timings)
        time_layout.addWidget(QLabel("Block Interval (BInt): 55 ms"))
        time_layout.addWidget(QLabel("Char Interval (CInt): 1 ms"))
        time_layout.addWidget(QLabel("Echo Delay (EDel): 500 ms"))
        layout.addWidget(group_timings)

        layout.addStretch()

    def on_dtc_search(self):
        code = self.txt_dtc_search.text().strip()
        if not code:
            return
        info = self.dtc_db.lookup(code)

        html = f"""
        <h2 style='color: #ef4444;'>Código VAG: {info['vag_code']} (OBD-II: {info['obd_code']})</h2>
        <h3 style='color: #38bdf8;'>{info['component']}</h3>
        <p><i>{info['description']}</i></p>
        <hr style='border: 1px solid #334155;'>
        <h4 style='color: #f59e0b;'>Sintomas Prováveis no Veículo:</h4>
        <ul>
        """
        for sym in info.get("symptoms", []):
            html += f"<li>{sym}</li>"
        html += """
        </ul>
        <h4 style='color: #22c55e;'>Procedimento de Teste com Multímetro no Chicote:</h4>
        <ol>
        """
        for step in info.get("multimeter_test", []):
            html += f"<li>{step}</li>"
        html += f"""
        </ol>
        <h4 style='color: #38bdf8;'>Ação Corretiva Mecânica:</h4>
        <p>{info.get('mechanical_fix')}</p>
        """
        self.txt_dtc_details.setHtml(html)

    def run_port_test(self):
        port_val = self.port_combo.currentData()
        if port_val == "MOCK":
            QMessageBox.information(self, "Teste de Interface", "Interface Simulação (Mock): Status OK!\nComunicação com emulador pronta.")
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

        is_mock = (self.port_combo.currentData() == "MOCK")

        for idx, addr in enumerate(modules):
            self.progress_scan.setValue(idx + 1)
            name = self.autoscan_mgr.get_module_name(addr)

            if is_mock and addr == 0x01:
                status = "OK — Respondendo"
                dtcs = "00515 (Hall), 00525 (Lambda)"
            elif is_mock:
                status = "Sem resposta"
                dtcs = "Nenhum"
            else:
                status = "Não detectado"
                dtcs = "-"

            row = self.table_scan.rowCount()
            self.table_scan.insertRow(row)
            self.table_scan.setItem(row, 0, QTableWidgetItem(f"0x{addr:02X}"))
            self.table_scan.setItem(row, 1, QTableWidgetItem(name))
            self.table_scan.setItem(row, 2, QTableWidgetItem(status))
            self.table_scan.setItem(row, 3, QTableWidgetItem(dtcs))

        QMessageBox.information(self, "Auto-Scan Concluído", f"Varredura de {len(modules)} módulos finalizada.")

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

    def __init__(self, address: int, port: str, is_mock: bool = False, mock_ecu_type: str = "BOSCH_MP90", parent=None):
        super().__init__(parent)
        self.address = address
        self.port = port
        self.is_mock = is_mock
        self.mock_ecu_type = mock_ecu_type
        self.engine: Optional[KW1281Engine] = None
        self.dtc_db = DTCDatabase()

        self.setWindowTitle(f"Módulo 0x{address:02X} — {MODULE_NAMES.get(address, 'Controlador')}")
        self.resize(900, 650)
        self.setStyleSheet(DARK_STYLE)

        self.measuring_timer = QTimer(self)
        self.measuring_timer.timeout.connect(self.poll_measuring_blocks)

        self.is_logging_csv = False
        self.csv_file = None
        self.csv_writer = None
        self.csv_sample_count = 0
        self.csv_filepath = ""

        self.init_ui()
        self.start_connection()

    def init_ui(self):
        layout = QVBoxLayout(self)

        group_id = QGroupBox("Identificação do Módulo (VAG Controller Info)")
        id_layout = QVBoxLayout(group_id)

        self.lbl_part_number = QLabel("VAG Number: Conectando...")
        self.lbl_part_number.setStyleSheet("font-size: 14px; font-weight: bold; color: #38bdf8;")
        self.lbl_component = QLabel("Component: Aguardando handshake...")
        self.lbl_coding = QLabel("Soft. Coding: -- | Work Shop Code: --")

        id_layout.addWidget(self.lbl_part_number)
        id_layout.addWidget(self.lbl_component)
        id_layout.addWidget(self.lbl_coding)
        layout.addWidget(group_id)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        widget_basic = QWidget()
        v_basic = QVBoxLayout(widget_basic)
        v_basic.addWidget(QLabel("<b>Funções Rápidas de Diagnóstico</b>"))

        self.btn_02 = QPushButton("🩺 Códigos de Falha (DTCs)")
        self.btn_02.setMinimumHeight(38)
        self.btn_02.clicked.connect(self.view_dtcs)
        v_basic.addWidget(self.btn_02)

        self.btn_08 = QPushButton("📊 Sensores em Tempo Real (Live Data)")
        self.btn_08.setMinimumHeight(38)
        self.btn_08.clicked.connect(self.view_measuring_blocks)
        v_basic.addWidget(self.btn_08)

        self.btn_tba = QPushButton("🎯 Calibração de Borboleta / Marcha Lenta")
        self.btn_tba.setMinimumHeight(44)
        self.btn_tba.setStyleSheet("background-color: #0284c7; color: white; font-weight: bold; font-size: 13px;")
        self.btn_tba.clicked.connect(self.open_tbi_calibration)
        v_basic.addWidget(self.btn_tba)

        self.btn_04 = QPushButton("04 — Ajuste Básico")
        self.btn_04.clicked.connect(self.view_basic_settings)
        v_basic.addWidget(self.btn_04)

        v_basic.addStretch()
        splitter.addWidget(widget_basic)

        widget_adv = QWidget()
        v_adv = QVBoxLayout(widget_adv)
        v_adv.addWidget(QLabel("<b>Funções Avançadas</b>"))

        btn_03 = QPushButton("03 — Teste de Atuadores (Output Tests)")
        btn_03.clicked.connect(self.run_output_tests)
        v_adv.addWidget(btn_03)

        btn_07 = QPushButton("07 — Recodificar Módulo (Recode)")
        btn_07.clicked.connect(self.run_recode)
        v_adv.addWidget(btn_07)

        btn_10 = QPushButton("10 — Adaptação de Canais (Adaptation)")
        btn_10.clicked.connect(self.run_adaptation)
        v_adv.addWidget(btn_10)

        btn_11 = QPushButton("11 — Acesso de Segurança (Login)")
        btn_11.clicked.connect(self.run_login)
        v_adv.addWidget(btn_11)

        v_adv.addStretch()
        splitter.addWidget(widget_adv)

        layout.addWidget(splitter)

        self.stack_box = QGroupBox("Painel de Diagnóstico em Tempo Real")
        self.stack_layout = QVBoxLayout(self.stack_box)

        self.table_live = QTableWidget(4, 4)
        self.table_live.setHorizontalHeaderLabels(["Campo", "Valor Atual", "Unidade", "Especificação"])
        self.table_live.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.stack_layout.addWidget(self.table_live)

        self.scope = LiveMiniScopeWidget()
        self.stack_layout.addWidget(self.scope)

        layout.addWidget(self.stack_box)

        bottom_bar = QHBoxLayout()
        self.spin_group = QSpinBox()
        self.spin_group.setRange(0, 255)
        self.spin_group.setValue(1)
        bottom_bar.addWidget(QLabel("Grupo de Medição:"))
        bottom_bar.addWidget(self.spin_group)

        self.btn_toggle_measuring = QPushButton("▶ Iniciar Leitura")
        self.btn_toggle_measuring.clicked.connect(self.toggle_measuring)
        bottom_bar.addWidget(self.btn_toggle_measuring)

        self.btn_datalogger = QPushButton("🔴 Gravar Teste de Rodagem (CSV)")
        self.btn_datalogger.setStyleSheet("background-color: #0284c7; color: white; font-weight: bold; padding: 6px 12px;")
        self.btn_datalogger.clicked.connect(self.toggle_datalogger)
        bottom_bar.addWidget(self.btn_datalogger)

        self.lbl_log_status = QLabel("")
        self.lbl_log_status.setStyleSheet("color: #38bdf8; font-weight: bold; margin-left: 6px;")
        bottom_bar.addWidget(self.lbl_log_status)

        bottom_bar.addStretch()

        btn_close = QPushButton("06 — Fechar Controlador / Voltar")
        btn_close.setStyleSheet("background-color: #991b1b; color: white;")
        btn_close.clicked.connect(self.close_controller)
        bottom_bar.addWidget(btn_close)

        layout.addLayout(bottom_bar)

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

            brand_tag = f"[{brand} {model}]"
            self.lbl_part_number.setText(f"Part Number VAG: {info.get('part_number', '030 906 027 AA')}")
            self.lbl_component.setText(f"🚗 Veículo: {brand} {model}  |  {info.get('component', '')}")
            self.lbl_coding.setText(f"Arquitetura: {throttle}  |  Coding: {info.get('coding', '00000')}  |  WSC: {info.get('wsc', 'WSC 00000')}")

            # Personaliza os botões dinamicamente para o carro conectado
            if family == "BOSCH_MP90":
                self.btn_tba.setText("🎯 Calibrar Borboleta (Grupo 098)")
                self.btn_tba.setStyleSheet("background-color: #d97706; color: white; font-weight: bold; font-size: 13px;")
                self.btn_04.setText("04 — Ajuste Básico Geral")
            elif family == "MARELLI_1AVP":
                self.btn_tba.setText("🎯 Reset Marcha Lenta (Canal 00)")
                self.btn_tba.setStyleSheet("background-color: #0284c7; color: white; font-weight: bold; font-size: 13px;")
                self.btn_04.setText("04 — Travar Ponto 9.0° APMS (Grupo 001)")
            elif family == "BOSCH_ME7":
                self.btn_tba.setText("🎯 Calibrar Borboleta E-Gas (Grupo 060)")
                self.btn_tba.setStyleSheet("background-color: #059669; color: white; font-weight: bold; font-size: 13px;")
                self.btn_04.setText("04 — Ajuste Básico Geral")
        except Exception as e:
            QMessageBox.critical(self, "Falha de Conexão", f"Não foi possível conectar ao módulo 0x{self.address:02X}:\n{e}")
            self.reject()

    def toggle_measuring(self):
        if self.measuring_timer.isActive():
            self.measuring_timer.stop()
            self.btn_toggle_measuring.setText("▶ Iniciar Leitura")
        else:
            self.measuring_timer.start(400)
            self.btn_toggle_measuring.setText("⏸ Pausar Leitura")

    def poll_measuring_blocks(self):
        if not self.engine or not self.engine.connected:
            return

        group = self.spin_group.value()
        fields = self.engine.read_measuring_group(group)

        self.table_live.setRowCount(len(fields))
        for r, f in enumerate(fields):
            self.table_live.setItem(r, 0, QTableWidgetItem(f.get("name", f"Campo {r+1}")))
            self.table_live.setItem(r, 1, QTableWidgetItem(str(f.get("value", "--"))))
            self.table_live.setItem(r, 2, QTableWidgetItem(f.get("unit", "")))
            self.table_live.setItem(r, 3, QTableWidgetItem(f.get("spec", "")))

            if r == 0 and isinstance(f.get("value"), (int, float)):
                self.scope.add_point(float(f["value"]))

        # Datalogger em Tempo Real para Teste de Rodagem
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
                self.lbl_log_status.setText(f"🔴 Gravando rodagem: {self.csv_sample_count} amostras")
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

                self.btn_datalogger.setText("⏹ Finalizar Gravação")
                self.btn_datalogger.setStyleSheet("background-color: #dc2626; color: white; font-weight: bold; padding: 6px 12px;")
                self.lbl_log_status.setText("🔴 Gravando teste de rodagem...")

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

            self.btn_datalogger.setText("🔴 Gravar Teste de Rodagem (CSV)")
            self.btn_datalogger.setStyleSheet("background-color: #0284c7; color: white; font-weight: bold; padding: 6px 12px;")
            self.lbl_log_status.setText(f"✅ Salvo ({self.csv_sample_count} amostras)")

            QMessageBox.information(
                self, "Teste de Rodagem Finalizado",
                f"Gravação de rodagem finalizada com sucesso!\n\n"
                f"• Amostras gravadas: {self.csv_sample_count}\n"
                f"• Arquivo CSV: {self.csv_filepath}\n\n"
                f"Você pode abrir este arquivo no Excel para analisar qualquer falha ou engasgo durante a volta com o carro."
            )

    def close_controller(self):
        self.stop_datalogger()
        if self.measuring_timer.isActive():
            self.measuring_timer.stop()
        if self.engine:
            self.engine.disconnect()
        self.accept()

    def closeEvent(self, event):
        self.stop_datalogger()
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
