"""
Parser de arquivos de rótulos (.LBL) do VCDS / VAG-COM.
Permite carregar arquivos de labels diretamente da instalação do VCDS-Lite
ou de um repositório local para traduzir blocos de medição brutos em nomes
legíveis com faixas ideais de tolerância.
"""

import os
import re
from typing import Dict, Any, Optional, List

DEFAULT_LABELS_PATH = r"C:\Ross-Tech\VCDS-Lite\Labels"


class VCDSLabelParser:
    """
    Parser e gerenciador de arquivos .LBL do VCDS.
    """

    def __init__(self, labels_dir: str = DEFAULT_LABELS_PATH):
        self.labels_dir = labels_dir
        self.cache: Dict[str, Dict[str, Any]] = {}

    def find_label_file(self, part_number: str) -> Optional[str]:
        """
        Localiza o arquivo .lbl correspondente ao Part Number da ECU (ex: '030-906-032-AKK' ou '030906032').
        """
        if not os.path.exists(self.labels_dir):
            return None

        clean_pn = part_number.replace(" ", "").upper()
        # Normaliza formato com hífens se necessário (ex: 030906032 -> 030-906-032)
        candidates = [clean_pn]
        if len(clean_pn) >= 9 and "-" not in clean_pn:
            formatted = f"{clean_pn[:3]}-{clean_pn[3:6]}-{clean_pn[6:]}"
            candidates.append(formatted)

        for candidate in candidates:
            # 1. Busca exata
            direct_path = os.path.join(self.labels_dir, f"{candidate}.lbl")
            if os.path.exists(direct_path):
                return direct_path

            # 2. Busca por prefixo no diretório
            for filename in os.listdir(self.labels_dir):
                if filename.upper().startswith(candidate) and filename.lower().endswith(".lbl"):
                    return os.path.join(self.labels_dir, filename)

        return None

    def parse_label_file(self, file_path: str) -> Dict[str, Any]:
        """
        Interpreta o arquivo .LBL e retorna um dicionário estruturado por grupo e campo.
        """
        if file_path in self.cache:
            return self.cache[file_path]

        result = {
            "file": file_path,
            "title": "",
            "redirect": None,
            "groups": {}
        }

        try:
            with open(file_path, "r", encoding="latin-1", errors="replace") as f:
                lines = f.readlines()
        except Exception:
            return result

        for line in lines:
            line = line.strip()
            if not line or line.startswith(";"):
                continue

            # Verifica REDIRECT
            if line.upper().startswith("REDIRECT,"):
                parts = line.split(",")
                if len(parts) >= 2:
                    result["redirect"] = parts[1].strip()
                continue

            # Cabeçalho de componente
            if line.startswith("#") or line.startswith("\xa3") or line.startswith("$"):
                result["title"] += " " + line.strip("#\"' $")
                continue

            # Linha de campo de medição: <grupo>,<campo>,<descrição>,<especificação>
            parts = [p.strip() for p in line.split(",")]
            if len(parts) >= 3 and parts[0].isdigit():
                group_num = int(parts[0])
                field_num = int(parts[1]) if parts[1].isdigit() else 0
                desc = parts[2]
                spec = parts[3] if len(parts) >= 4 else ""

                if group_num not in result["groups"]:
                    result["groups"][group_num] = {
                        "header": "",
                        "fields": {}
                    }

                if field_num == 0:
                    result["groups"][group_num]["header"] = desc
                else:
                    result["groups"][group_num]["fields"][field_num] = {
                        "name": desc,
                        "spec": spec
                    }

        self.cache[file_path] = result
        return result

    def get_field_info(self, part_number: str, group: int, field: int) -> Optional[Dict[str, str]]:
        """
        Recupera o nome e especificação de um campo de medição para um dado Part Number.
        """
        lbl_file = self.find_label_file(part_number)
        if not lbl_file:
            return None

        parsed = self.parse_label_file(lbl_file)
        if parsed.get("redirect"):
            # Segue redirecionamento se houver
            target_file = os.path.join(self.labels_dir, parsed["redirect"])
            if os.path.exists(target_file):
                parsed = self.parse_label_file(target_file)

        group_data = parsed.get("groups", {}).get(group)
        if group_data:
            return group_data.get("fields", {}).get(field)
        return None
