"""
Gerenciador de Auto-Scan do Scanner-VW.
Lê os perfis de chassis de AutoScan.txt (do VCDS-Lite ou local) e executa
varredura sequencial em todos os módulos do veículo com relatório de falhas.
"""

import os
from typing import Dict, List, Any

DEFAULT_AUTOSCAN_PATH = r"C:\Ross-Tech\VCDS-Lite\AutoScan.txt"

MODULE_NAMES = {
    0x01: "01 - Motor (Engine / Injeção)",
    0x02: "02 - Transmissão Automática",
    0x03: "03 - Freios ABS",
    0x08: "08 - Climatização (Ar-Condicionado)",
    0x09: "09 - Central Eletrônica (BCM)",
    0x15: "15 - Airbags",
    0x17: "17 - Painel de Instrumentos (Cluster)",
    0x19: "19 - Gateway CAN / K-Line",
    0x25: "25 - Imobilizador (Immo)",
    0x35: "35 - Trava Central",
    0x46: "46 - Conforto e Conveniência",
    0x56: "56 - Rádio",
}


class AutoScanManager:

    def __init__(self, autoscan_file: str = DEFAULT_AUTOSCAN_PATH):
        self.autoscan_file = autoscan_file
        self.chassis_profiles: Dict[str, Dict[str, Any]] = {}
        self.load_profiles()

    def load_profiles(self):
        # Carrega perfis básicos de fábrica
        self.chassis_profiles = {
            "5Y": {"name": "VW Gol Special / G2", "modules": [0x01]},
            "5W": {"name": "VW Gol / Parati / Saveiro G3/G4", "modules": [0x01, 0x03, 0x15, 0x17, 0x25, 0x46]},
            "1J": {"name": "VW Golf / Bora IV", "modules": [0x01, 0x02, 0x03, 0x08, 0x15, 0x17, 0x19, 0x25, 0x46, 0x56]},
            "6N": {"name": "VW Polo Classic", "modules": [0x01, 0x02, 0x03, 0x15, 0x17, 0x25, 0x46, 0x56]},
        }

        if os.path.exists(self.autoscan_file):
            try:
                with open(self.autoscan_file, "r", encoding="latin-1") as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith(";"):
                            continue
                        parts = [p.strip() for p in line.split(",")]
                        if len(parts) >= 3 and len(parts[0]) <= 3:
                            code = parts[0]
                            desc = parts[1]
                            modules = []
                            for m in parts[2:]:
                                try:
                                    modules.append(int(m, 16))
                                except ValueError:
                                    pass
                            if modules:
                                self.chassis_profiles[code] = {
                                    "name": desc,
                                    "modules": modules
                                }
            except Exception:
                pass

    def get_module_name(self, address: int) -> str:
        return MODULE_NAMES.get(address, f"Módulo 0x{address:02X}")
