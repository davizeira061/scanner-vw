"""
Decodificador de fórmulas de blocos de medição (Measuring Blocks) do protocolo KW1281.
Converte a trinca de bytes (Tipo de Fórmula `a`, Byte `b`, Byte `c`) em valores físicos
com unidades de engenharia (RPM, °C, %, mbar, V, etc.).
"""

from typing import Dict, Any, Tuple


class KW1281SensorDecoder:
    """
    Decodificador universal das fórmulas VAG para blocos de medição KWP1281.
    """

    @staticmethod
    def decode_field(formula_type: int, b: int, c: int) -> Dict[str, Any]:
        """
        Converte os bytes brutos (a, b, c) na grandeza correspondente.
        Retorna dicionário com: valor formatado, valor numérico, unidade e descrição.
        """
        # Proteção contra bytes fora de 0-255
        b = b & 0xFF
        c = c & 0xFF

        val_num = 0.0
        unit = ""
        text = ""

        if formula_type == 1:  # RPM (Rotação do Motor)
            val_num = round(b * 0.2 * c, 1) if c != 0 else round(b * 0.2, 1)
            unit = "RPM"
            text = f"{int(val_num)} RPM"

        elif formula_type == 2:  # Carga / Posição de Borboleta (%)
            val_num = round((b * 0.002 * c) if c != 0 else (b * 100.0 / 255.0), 1)
            unit = "%"
            text = f"{val_num:.1f} %"

        elif formula_type == 3:  # Ângulo de Abertura / Ponto (° CA)
            val_num = round(b * 0.75, 1)
            unit = "°"
            text = f"{val_num:.1f} °"

        elif formula_type == 4:  # Ângulo de Ignição / Avanço (° APMS)
            val_num = round((b - 78) * 0.5, 1) if b >= 78 else round((78 - b) * -0.5, 1)
            unit = "° APMS"
            text = f"{val_num:.1f} ° APMS"

        elif formula_type == 5:  # Temperatura do Líquido de Arrefecimento (°C)
            val_num = round((b - 100) * 0.1, 1) if c != 0 else float(b - 50)
            unit = "°C"
            text = f"{val_num:.1f} °C"

        elif formula_type == 6:  # Tensão Sonda Lambda (0 a 1.0 V)
            val_num = round(b * 0.001 * c if c != 0 else b * 0.00488, 3)
            unit = "V"
            text = f"{val_num:.3f} V"

        elif formula_type == 7:  # Velocidade (km/h)
            val_num = round(b * 0.01 * c, 1) if c != 0 else float(b)
            unit = "km/h"
            text = f"{int(val_num)} km/h"

        elif formula_type == 8:  # Tensão da Bateria (V)
            val_num = round(b * 0.01 * c if c != 0 else b * 0.02, 2)
            unit = "V"
            text = f"{val_num:.2f} V"

        elif formula_type == 9:  # Tensão / Sonda Lambda
            val_num = round((b - 128) * 100.0 / 128.0, 1)
            unit = "%"
            text = f"{val_num:+.1f} %"

        elif formula_type == 10:  # Bits de Estado / Interruptores (Binário)
            bits_str = f"{b:08b}"
            unit = "bits"
            text = bits_str

        elif formula_type == 11:  # Temperatura do Ar de Admissão (°C)
            val_num = round(0.75 * (b - 48), 1)
            unit = "°C"
            text = f"{val_num:.1f} °C"

        elif formula_type == 12:  # Pressão do Coletor - MAP (mbar)
            val_num = round(b * 2.0 if c == 0 else b * c * 0.01, 1)
            unit = "mbar"
            text = f"{int(val_num)} mbar"

        elif formula_type == 15:  # Tempo de Injeção (ms)
            val_num = round(b * 0.05 if c == 0 else b * c * 0.001, 2)
            unit = "ms"
            text = f"{val_num:.2f} ms"

        elif formula_type == 20:  # Regulação Lambda (%)
            val_num = round((b - 128) * 100.0 / 128.0, 1)
            unit = "%"
            text = f"{val_num:+.1f} %"

        elif formula_type == 36:  # Odômetro / Distância (km)
            val_num = float(b * 2560 + c * 10)
            unit = "km"
            text = f"{int(val_num)} km"

        else:
            # Fórmula padrão genérica
            val_num = float(b)
            unit = "raw"
            text = f"{b} (tipo {formula_type})"

        return {
            "type_id": formula_type,
            "raw_b": b,
            "raw_c": c,
            "value": val_num,
            "unit": unit,
            "text": text
        }

    @staticmethod
    def decode_1avp_group_000(raw_bytes: list) -> list:
        """
        Decodificação especializada para o Grupo 000 da Magneti Marelli 1AVP (Gol G2 1.0 8v).
        O Grupo 000 retorna 10 campos de 0 a 255 com mapeamento estático:
        Campo 1: Temperatura do Motor (ECT)
        Campo 2: Tensão da Bateria
        Campo 3: Posição da Borboleta (TPS)
        Campo 4: Pressão Absoluta no Coletor (MAP)
        Campo 5: Rotação do Motor (RPM)
        Campo 6: Avanço de Ignição
        Campo 7: Sonda Lambda
        Campo 8: Aprendizado de Marcha Lenta
        Campo 9: Adaptação de Mistura
        Campo 10: Status / Interruptores
        """
        if len(raw_bytes) < 10:
            return []

        fields = []
        # 1: Temp ECT
        ect = raw_bytes[0] - 50
        fields.append({"name": "Temp. Motor (ECT)", "value": ect, "unit": "°C", "min": 80, "max": 105})

        # 2: Tensão Bateria
        volts = round(raw_bytes[1] * 0.02 + 8.0, 2)
        fields.append({"name": "Tensão da Bateria", "value": volts, "unit": "V", "min": 13.2, "max": 14.5})

        # 3: TPS Borboleta
        tps = round(raw_bytes[2] * 0.4, 1)
        fields.append({"name": "Posição Borboleta (TPS)", "value": tps, "unit": "%", "min": 0.0, "max": 4.0})

        # 4: MAP
        map_val = raw_bytes[3] * 4
        fields.append({"name": "Pressão Coletor (MAP)", "value": map_val, "unit": "mbar", "min": 280, "max": 420})

        # 5: RPM
        rpm = raw_bytes[4] * 40
        fields.append({"name": "Rotação (RPM)", "value": rpm, "unit": "RPM", "min": 850, "max": 950})

        # 6: Avanço Ignição
        timing = round((raw_bytes[5] - 78) * 0.5, 1)
        fields.append({"name": "Ponto de Ignição", "value": timing, "unit": "° APMS", "min": 6.0, "max": 12.0})

        # 7: Sonda Lambda
        sonda = round(raw_bytes[6] * 0.00488, 3)
        fields.append({"name": "Sonda Lambda", "value": sonda, "unit": "V", "min": 0.1, "max": 0.9})

        # 8: Marcha Lenta
        idle_step = raw_bytes[7]
        fields.append({"name": "Passo Marcha Lenta", "value": idle_step, "unit": "passos", "min": 15, "max": 65})

        # 9: Adaptação de Mistura
        fuel_trim = round((raw_bytes[8] - 128) * 100.0 / 128.0, 1)
        fields.append({"name": "Correção de Mistura", "value": fuel_trim, "unit": "%", "min": -10.0, "max": 10.0})

        # 10: Status
        status_bin = f"{raw_bytes[9]:08b}"
        fields.append({"name": "Interruptores / Status", "value": status_bin, "unit": "bits", "min": 0, "max": 0})

        return fields
