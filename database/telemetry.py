"""
Módulo de Telemetria e Registro de Sessões de Diagnóstico.
Armazena dados de leitura ao vivo e códigos de falha em banco SQLite local,
com suporte para exportação para CSV e JSON para análise e relatórios.
"""

import os
import csv
import json
import sqlite3
import datetime
from typing import List, Dict, Any, Optional

DEFAULT_DB_PATH = os.path.join(os.path.dirname(__file__), "telemetry.db")


class TelemetryLogger:
    """
    Gravador de telemetria de sensores e histórico de diagnósticos.
    """

    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self.db_path = db_path
        self.current_session_id: Optional[int] = None
        self._init_db()

    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            # Tabela de Sessões
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    start_time TEXT NOT NULL,
                    end_time TEXT,
                    vehicle_model TEXT,
                    ecu_part_number TEXT,
                    ecu_component TEXT,
                    notes TEXT
                )
            """)
            # Tabela de Dados de Telemetria
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS telemetry_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER NOT NULL,
                    timestamp TEXT NOT NULL,
                    group_num INTEGER NOT NULL,
                    field_name TEXT NOT NULL,
                    value REAL,
                    unit TEXT,
                    raw_text TEXT,
                    FOREIGN KEY (session_id) REFERENCES sessions (id)
                )
            """)
            # Tabela de Histórico de DTCs
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS dtc_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER NOT NULL,
                    timestamp TEXT NOT NULL,
                    dtc_code TEXT NOT NULL,
                    description TEXT,
                    status_byte INTEGER,
                    FOREIGN KEY (session_id) REFERENCES sessions (id)
                )
            """)
            conn.commit()
        finally:
            conn.close()

    def start_session(self, vehicle: str = "VW Gol G2 1.0 8v", ecu_pn: str = "", ecu_comp: str = "", notes: str = "") -> int:
        """Inicia uma nova sessão de diagnóstico."""
        now = datetime.datetime.now().isoformat()
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO sessions (start_time, vehicle_model, ecu_part_number, ecu_component, notes)
                VALUES (?, ?, ?, ?, ?)
            """, (now, vehicle, ecu_pn, ecu_comp, notes))
            conn.commit()
            self.current_session_id = cursor.lastrowid
        finally:
            conn.close()
        return self.current_session_id

    def log_measuring_fields(self, group: int, fields: List[Dict[str, Any]]):
        """Grava uma amostragem de dados de sensores na sessão ativa."""
        if not self.current_session_id:
            self.start_session()

        now = datetime.datetime.now().isoformat()
        rows = []
        for f in fields:
            name = f.get("name", "Desconhecido")
            val = f.get("value")
            unit = f.get("unit", "")
            raw = f.get("text", str(val))
            num_val = float(val) if isinstance(val, (int, float)) else None
            rows.append((self.current_session_id, now, group, name, num_val, unit, raw))

        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.executemany("""
                INSERT INTO telemetry_data (session_id, timestamp, group_num, field_name, value, unit, raw_text)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, rows)
            conn.commit()
        finally:
            conn.close()

    def log_dtc(self, dtc_code: str, description: str, status_byte: int = 0):
        """Registra uma falha detectada."""
        if not self.current_session_id:
            self.start_session()

        now = datetime.datetime.now().isoformat()
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO dtc_history (session_id, timestamp, dtc_code, description, status_byte)
                VALUES (?, ?, ?, ?, ?)
            """, (self.current_session_id, now, dtc_code, description, status_byte))
            conn.commit()
        finally:
            conn.close()

    def end_session(self):
        """Encerra a sessão ativa."""
        if self.current_session_id:
            now = datetime.datetime.now().isoformat()
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE sessions SET end_time = ? WHERE id = ?
                """, (now, self.current_session_id))
                conn.commit()
            finally:
                conn.close()
            self.current_session_id = None

    def export_session_to_csv(self, session_id: int, output_file: str) -> bool:
        """Exporta os dados de uma sessão para um arquivo CSV formatado."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT timestamp, group_num, field_name, value, unit, raw_text
                FROM telemetry_data
                WHERE session_id = ?
                ORDER BY timestamp ASC
            """, (session_id,))
            rows = cursor.fetchall()
        finally:
            conn.close()

        if not rows:
            return False

        with open(output_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Timestamp", "Grupo", "Sensor", "Valor Numérico", "Unidade", "Texto Bruto"])
            writer.writerows(rows)
        return True
