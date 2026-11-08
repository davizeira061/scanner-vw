"""
Banco de dados e motor de diagnóstico guiado de DTCs (Códigos de Falha).
Cruza o código numérico VAG (ex: 00515) e código OBD-II (P0340) com informações
práticas de sintomas mecânicos, testes elétricos de bancada com multímetro e
procedimentos de reparação.
"""

import os
import json
from typing import Dict, Any, Optional

DEFAULT_DTC_FILE = os.path.join(os.path.dirname(__file__), "dtc_data.json")


class DTCDatabase:
    """
    Gerenciador e consultor da base de conhecimento de códigos de erro automotivos.
    """

    def __init__(self, data_file: str = DEFAULT_DTC_FILE):
        self.data_file = data_file
        self.database: Dict[str, Dict[str, Any]] = {}
        self.load()

    def load(self) -> bool:
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, "r", encoding="utf-8") as f:
                    self.database = json.load(f)
                return True
            except Exception:
                self.database = {}
                return False
        return False

    def lookup(self, code: str) -> Dict[str, Any]:
        """
        Busca informações detalhadas de um código de falha (formatos aceitos: '00515', '515', 'P0340').
        """
        clean_code = code.strip().upper()
        # Normaliza 515 -> 00515
        if clean_code.isdigit():
            normalized = f"{int(clean_code):05d}"
        else:
            normalized = clean_code

        # 1. Busca por código VAG normalizado
        if normalized in self.database:
            return self.database[normalized]

        # 2. Busca reversa por código OBD-II (ex: P0340)
        for _, entry in self.database.items():
            if entry.get("obd_code", "").upper() == clean_code:
                return entry

        # Fallback genérico caso o código não esteja na base enriquecida
        return {
            "vag_code": normalized,
            "obd_code": "P----",
            "component": f"Falha VAG {normalized}",
            "description": "Código de falha detectado na memória da ECU.",
            "symptoms": ["Comportamento anômalo no módulo correspondente."],
            "multimeter_test": [
                "1. Consultar esquema elétrico da central.",
                "2. Verificar continuidade e integridade do chicote para o atuador/sensor.",
                "3. Medir tensão de alimentação e sinal."
            ],
            "mechanical_fix": "Inspecionar conectores, fusíveis e testar o componente com instrumento adequado."
        }
