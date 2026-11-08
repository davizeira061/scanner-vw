"""
Motor completo de implementação do protocolo KW1281 (Volkswagen / Audi / Seat / Skoda).
Implementa 100% das funções do VCDS-Lite:
- 01: Identificação de Módulo (Part Number, Componente, Codificação, WSC)
- 02: Leitura de Códigos de Falha (DTCs)
- 03: Teste de Atuadores (Output Tests)
- 04: Ajuste Básico (Basic Settings: Trava de ponto estático, calibração TBA)
- 05: Limpeza de Falhas (Clear Codes)
- 06: Fim de Sessão (Close Controller)
- 07: Codificação de Módulo (Recode)
- 08: Blocos de Medição (Measuring Blocks) com suporte a múltiplos grupos e labels
- 09: Keep-Alive (ACK contínuo)
- 10: Adaptação de Canais (Leitura e Gravação de parâmetros NVRAM)
- 11: Login / Security Access (Acesso Seguro com código de 5 dígitos)
"""

import time
import logging
from typing import Optional, List, Dict, Any, Tuple
from core.hardware import KLineSerialInterface, MockECUKLineInterface
from core.sensor_decoder import KW1281SensorDecoder
from core.lbl_parser import VCDSLabelParser

logger = logging.getLogger("scanner_vw.kw1281")


class KW1281ProtocolError(Exception):
    pass


class KW1281Engine:
    """
    Máquina de estados e motor de execução do protocolo KW1281.
    """

    CMD_ECU_ID = 0x00
    CMD_ACK = 0x09             # Keep-Alive / Acknowledge
    CMD_READ_DTC = 0x07        # Leitura de memória de avarias
    CMD_CLEAR_DTC = 0x05       # Limpeza de avarias
    CMD_MEASURING_BLOCK = 0x29 # Leitura de bloco de medição
    CMD_BASIC_SETTING = 0x28   # Ajuste básico
    CMD_OUTPUT_TESTS = 0x04    # Teste de atuadores
    CMD_RECODE = 0x0C          # Codificação de software
    CMD_ADAPT_READ = 0x21      # Leitura de canal de adaptação
    CMD_ADAPT_SAVE = 0x22      # Gravação de canal de adaptação
    CMD_LOGIN = 0x2B           # Login / Security Access
    CMD_END_SESSION = 0x06     # Fim de sessão de diagnóstico

    def __init__(self, serial_interface=None, mock_mode: bool = False, part_number_hint: str = "", mock_ecu_type: str = "BOSCH_MP90"):
        self.mock_mode = mock_mode
        self.mock_ecu = MockECUKLineInterface(ecu_type=mock_ecu_type) if mock_mode else None
        self.ser = serial_interface
        self.block_counter = 0
        self.connected = False
        self.current_address = 0x01
        self.ecu_info = {
            "part_number": "",
            "component": "",
            "coding": "",
            "wsc": "",
            "extra": []
        }
        self.lbl_parser = VCDSLabelParser()
        self.part_number_hint = part_number_hint

    def connect(self, address: int = 0x01) -> bool:
        """
        Executa o handshake de 5 bauds e estabelece a sessão KW1281 com o módulo.
        """
        self.current_address = address
        if self.mock_mode:
            logger.info("[MOCK] Conectando à ECU simulada no endereço 0x%02X...", address)
            time.sleep(0.05)
            self.connected = True
            self.ecu_info["part_number"] = self.mock_ecu.ecu_id
            self.ecu_info["component"] = self.mock_ecu.component
            self.ecu_info["coding"] = self.mock_ecu.coding
            self.ecu_info["wsc"] = self.mock_ecu.wsc
            self.block_counter = 1
            return True

        if not self.ser or not self.ser.is_open:
            raise KW1281ProtocolError("Interface serial não está aberta.")

        # 1. 5-baud Slow Init
        self.ser.send_5baud_slow_init(address)

        # 2. Aguarda byte de sincronismo (0x55)
        sync = self.ser.read_byte(timeout=2.0)
        if sync != 0x55:
            raise KW1281ProtocolError(f"Falha de sincronização. Esperado 0x55, recebido: {hex(sync) if sync else 'None'}")

        # 3. Lê KeyBytes (KB1 e KB2)
        kb1 = self.ser.read_byte(timeout=1.0)
        kb2 = self.ser.read_byte(timeout=1.0)
        if kb1 is None or kb2 is None:
            raise KW1281ProtocolError("Timeout aguardando KeyBytes da ECU.")

        logger.info("Sincronizado! KB1=0x%02X, KB2=0x%02X", kb1, kb2)

        # 4. Envia ACK (inversão de KB2)
        ack = (kb2 ^ 0xFF) & 0xFF
        time.sleep(0.010)
        self.ser.write_byte(ack)

        # 5. Recebe complemento do endereço
        addr_comp = self.ser.read_byte(timeout=1.0)
        expected_comp = (address ^ 0xFF) & 0xFF
        if addr_comp != expected_comp:
            logger.warning("Complemento de endereço inesperado: 0x%02X (esperado 0x%02X)", addr_comp, expected_comp)

        # 6. Lê blocos de identificação ASCII iniciais da ECU
        self._read_initial_ident()
        self.connected = True
        return True

    def _read_initial_ident(self):
        ident_strings = []
        for _ in range(5):
            block = self.read_block()
            if not block:
                break
            title = block.get("title", 0)
            data = block.get("data", [])
            if data and (title in (0xF6, 0xF7, 0x00)):
                text = "".join(chr(b) for b in data if 32 <= b <= 126).strip()
                if text:
                    ident_strings.append(text)
            self.send_ack()

        if ident_strings:
            self.ecu_info["part_number"] = ident_strings[0]
            if len(ident_strings) > 1:
                self.ecu_info["component"] = ident_strings[1]
            if len(ident_strings) > 2:
                self.ecu_info["extra"] = ident_strings[2:]

    def identify_ecu_system(self) -> Dict[str, Any]:
        """
        Identifica automaticamente a família da ECU conectada (Bosch Motronic MP9.0, Bosch ME 7.x,
        Magneti Marelli 1AVP/1AVB, etc.) com base nas strings de identificação recebidas no handshake.
        """
        comp = (self.ecu_info.get("component") or "").upper()
        pn = (self.ecu_info.get("part_number") or "").upper().replace(" ", "")
        extra = " ".join(self.ecu_info.get("extra", [])).upper()
        all_text = f"{comp} {pn} {extra}"

        # 1. Bosch Motronic MP 9.0 (Gol Mi 1.0 8v e 16v)
        if "MP9" in all_text or "MP 9.0" in all_text or "1HS908258" in all_text or "030906027" in pn:
            return {
                "family": "BOSCH_MP90",
                "brand": "Bosch",
                "model": "Motronic MP 9.0",
                "throttle_type": "Borboleta Semi-Eletrônica a Cabo c/ Motor DC Integrado",
                "recommended_tbi_mode": 3,  # Grupo 098
                "recommended_group": 98,
                "description": "Injeção Bosch Motronic MP 9.0 (Gol Mi). Corpo com cabo mecânico e motor elétrico integrado de marcha lenta. Alinhamento de Borboleta (TBA) no Grupo 098 (Status I.O. / ADP. OK)."
            }

        # 2. Bosch Motronic ME 7.x (E-Gas Drive-by-Wire sem cabo)
        if "ME7" in all_text or "ME 7" in all_text or "MOTRONIC ME" in all_text or "06A906032" in pn:
            return {
                "family": "BOSCH_ME7",
                "brand": "Bosch",
                "model": "Motronic ME 7.x",
                "throttle_type": "E-Gas 100% Eletrônico (Drive-by-Wire)",
                "recommended_tbi_mode": 2,  # Grupo 060
                "recommended_group": 60,
                "description": "Injeção Bosch Motronic ME 7.x com acelerador eletrônico E-Gas. Alinhamento de Borboleta via Ajuste Básico no Grupo 060 (TBA)."
            }

        # 3. Bosch Motronic Geral
        if "MOTRONIC" in all_text or "BOSCH" in all_text:
            return {
                "family": "BOSCH_GENERIC",
                "brand": "Bosch",
                "model": "Motronic",
                "throttle_type": "Borboleta Semi-Eletrônica a Cabo c/ Motor Integrado",
                "recommended_tbi_mode": 3,  # Grupo 098
                "recommended_group": 98,
                "description": "Injeção Bosch Motronic. Alinhamento de borboleta via Ajuste Básico no Grupo 098 (TBA)."
            }

        # 4. Magneti Marelli 1AVP / 1AVB
        if "1AVP" in all_text or "1AVB" in all_text or "IAW" in all_text or "MARELLI" in all_text or "030906032" in pn:
            return {
                "family": "MARELLI_1AVP",
                "brand": "Magneti Marelli",
                "model": "1AVP / 1AVB",
                "throttle_type": "Borboleta Mecânica a Cabo + Motor de Passo IACV 4 vias",
                "recommended_tbi_mode": 1,  # Reset EEPROM Canal 00
                "recommended_group": 1,   # Trava Ponto 9° Grupo 001
                "description": "Injeção Magneti Marelli 1AVP/1AVB. Reset de autoadaptação na EEPROM via Canal 00 e ciclo de chave (15s/30s). Trava de ponto em 9.0° APMS no Grupo 001."
            }

        # 5. Genérico VAG
        return {
            "family": "GENERIC_VAG",
            "brand": "VAG",
            "model": comp or "Módulo de Controle do Motor",
            "throttle_type": "Padrão VAG (Grupo 060 ou 098)",
            "recommended_tbi_mode": 3,
            "recommended_group": 98,
            "description": "Controlador de Injeção VAG."
        }

    def read_block(self) -> Optional[Dict[str, Any]]:
        if self.mock_mode:
            return {"size": 4, "counter": self.block_counter, "title": self.CMD_ACK, "data": []}

        raw_len = self.ser.read_byte(timeout=1.5)
        if raw_len is None:
            return None
        length = raw_len
        self.ser.write_byte((length ^ 0xFF) & 0xFF)

        payload = []
        for i in range(length - 1):
            b = self.ser.read_byte(timeout=1.0)
            if b is None:
                raise KW1281ProtocolError(f"Timeout durante leitura do bloco (byte {i}/{length})")
            payload.append(b)

            if i < (length - 2):
                self.ser.write_byte((b ^ 0xFF) & 0xFF)

        if not payload:
            return None

        # Validação do terminador ETX (0x03) do protocolo KWP1281
        end_byte = payload[-1]
        if end_byte != 0x03:
            logger.warning("Byte terminador de bloco desalinhado: 0x%02X (esperado 0x03 ETX). Descartando bloco corrompido.", end_byte)
            return None

        counter = payload[0]
        title = payload[1] if len(payload) > 1 else 0
        data = payload[2:-1] if len(payload) > 3 else []

        self.block_counter = counter
        return {
            "size": length,
            "counter": counter,
            "title": title,
            "data": data
        }

    def send_block(self, title: int, data: List[int] = None) -> bool:
        if self.mock_mode:
            self.block_counter = (self.block_counter + 1) & 0xFF
            return True

        if data is None:
            data = []

        self.block_counter = (self.block_counter + 1) & 0xFF
        length = 4 + len(data)

        block = [length, self.block_counter, title] + data + [0x03]

        for i, b in enumerate(block):
            self.ser.write_byte(b)
            if i < len(block) - 1:
                ack = self.ser.read_byte(timeout=1.0)
                expected = (b ^ 0xFF) & 0xFF
                if ack != expected:
                    logger.warning("ACK de transmissão desalinhado no byte %d: recebido 0x%02X, esperado 0x%02X", i, ack, expected)

        return True

    def send_ack(self) -> bool:
        return self.send_block(self.CMD_ACK)

    def read_measuring_group(self, group: int) -> List[Dict[str, Any]]:
        """Função 08: Lê grupos de 4 campos de dados."""
        if self.mock_mode:
            return self.mock_ecu.get_simulated_measuring_block(group)

        self.send_block(self.CMD_MEASURING_BLOCK, [group & 0xFF])
        block = self.read_block()

        if not block:
            return []

        data = block.get("data", [])
        if group == 0 and len(data) >= 10:
            return KW1281SensorDecoder.decode_1avp_group_000(data)

        fields = []
        pn = self.ecu_info.get("part_number") or self.part_number_hint
        for idx in range(0, min(12, len(data)), 3):
            field_num = (idx // 3) + 1
            if idx + 2 < len(data):
                f_type = data[idx]
                b = data[idx + 1]
                c = data[idx + 2]
                decoded = KW1281SensorDecoder.decode_field(f_type, b, c)

                lbl_info = self.lbl_parser.get_field_info(pn, group, field_num) if pn else None
                if lbl_info:
                    decoded["name"] = lbl_info.get("name", f"Campo {field_num}")
                    decoded["spec"] = lbl_info.get("spec", "")
                else:
                    decoded["name"] = f"Campo {field_num}"
                    decoded["spec"] = ""

                fields.append(decoded)

        self.send_ack()
        return fields

    def read_dtcs(self) -> List[Dict[str, Any]]:
        """Função 02: Lê códigos de avarias gravados."""
        if self.mock_mode:
            return [{"code": dtc, "status_byte": 0x23} for dtc in self.mock_ecu.dtcs]

        self.send_block(self.CMD_READ_DTC)
        dtcs = []

        while True:
            block = self.read_block()
            if not block:
                break

            data = block.get("data", [])
            if not data or block.get("title") == self.CMD_ACK:
                break

            for i in range(0, len(data), 3):
                if i + 1 < len(data):
                    high = data[i]
                    low = data[i + 1]
                    status = data[i + 2] if i + 2 < len(data) else 0
                    code_int = (high << 8) | low
                    if code_int == 0xFFFF or code_int == 0:
                        break
                    dtcs.append({
                        "code": f"{code_int:05d}",
                        "status_byte": status
                    })

            self.send_ack()
            break

        return dtcs

    def clear_dtcs(self) -> bool:
        """Função 05: Apaga a memória de avarias."""
        if self.mock_mode:
            self.mock_ecu.dtcs = []
            return True

        self.send_block(self.CMD_CLEAR_DTC)
        block = self.read_block()
        self.send_ack()
        return True

    def run_basic_settings(self, group: int = 1) -> List[Dict[str, Any]]:
        """Função 04: Ajuste Básico (Basic Settings - Trava Ponto / TBA)."""
        if self.mock_mode:
            # Em modo básico, a 1AVP trava o avanço estático em 9.0° APMS
            self.mock_ecu.timing_angle = 9.0
            return self.mock_ecu.get_simulated_measuring_block(group)

        self.send_block(self.CMD_BASIC_SETTING, [group & 0xFF])
        block = self.read_block()
        self.send_ack()
        return self.read_measuring_group(group)

    def trigger_next_output_test(self) -> Optional[str]:
        """Função 03: Teste Sequencial de Atuadores (Output Tests)."""
        if self.mock_mode:
            return self.mock_ecu.next_output_test()

        self.send_block(self.CMD_OUTPUT_TESTS)
        block = self.read_block()
        self.send_ack()
        if block and block.get("data"):
            actuator_text = "".join(chr(b) for b in block["data"] if 32 <= b <= 126).strip()
            return actuator_text or "Atuador Ativado"
        return None

    def read_adaptation_channel(self, channel: int) -> int:
        """Função 10: Leitura de Canal de Adaptação."""
        if self.mock_mode:
            return self.mock_ecu.adaptations.get(channel, 128)

        self.send_block(self.CMD_ADAPT_READ, [channel & 0xFF])
        block = self.read_block()
        self.send_ack()
        if block and len(block.get("data", [])) >= 2:
            val = (block["data"][0] << 8) | block["data"][1]
            return val
        return 128

    def save_adaptation_channel(self, channel: int, new_value: int) -> bool:
        """Função 10: Gravação em Canal de Adaptação com Travas de Segurança."""
        if channel == 0 and new_value != 0:
            raise ValueError("Canal 00 aceita exclusivamente o valor 00 para Restauração de Fábrica.")

        # Trava de segurança: Canal 01 (Marcha Lenta) restrito à faixa segura
        if channel == 1 and not (110 <= new_value <= 150):
            raise ValueError(f"Valor {new_value} fora da faixa segura de marcha lenta (permitido: 110 a 150, nominal 128).")

        if not (0 <= new_value <= 65535):
            raise ValueError("Valor de adaptação fora dos limites válidos (0 a 65535).")

        if self.mock_mode:
            self.mock_ecu.adaptations[channel] = new_value
            return True

        high = (new_value >> 8) & 0xFF
        low = new_value & 0xFF
        self.send_block(self.CMD_ADAPT_SAVE, [channel & 0xFF, high, low])
        block = self.read_block()
        self.send_ack()
        return True

    def reset_factory_adaptations(self) -> bool:
        """
        Função 10: Canal 00 - Reseta a tabela autoadaptativa de fábrica da ECU (1AVP / IAW / ME7).
        Apaga parâmetros aprendidos de marcha lenta, batente de borboleta e trim de combustível (STFT/LTFT).
        """
        return self.save_adaptation_channel(0, 0)

    def recode_module(self, new_coding: int, new_wsc: int = 0) -> bool:
        """Função 07: Recodificação de Software do Módulo (Coding) com Validação de Segurança."""
        if not (0 <= new_coding <= 65535):
            raise ValueError("Código de codificação inválido. Deve ser um número entre 00000 e 65535.")
        if not (0 <= new_wsc <= 65535):
            raise ValueError("Workshop Code (WSC) inválido. Deve ser um número entre 00000 e 65535.")

        if self.mock_mode:
            self.mock_ecu.coding = f"{new_coding:05d}"
            self.mock_ecu.wsc = f"WSC {new_wsc:05d}"
            self.ecu_info["coding"] = self.mock_ecu.coding
            self.ecu_info["wsc"] = self.mock_ecu.wsc
            return True

        high = (new_coding >> 8) & 0xFF
        low = new_coding & 0xFF
        w_high = (new_wsc >> 8) & 0xFF
        w_low = new_wsc & 0xFF
        self.send_block(self.CMD_RECODE, [high, low, w_high, w_low])
        block = self.read_block()
        self.send_ack()
        return True

    def login_security_access(self, login_code: int) -> bool:
        """Função 11: Acesso de Segurança / Login (5 dígitos)."""
        if not (0 <= login_code <= 65535):
            raise ValueError("Código de Login inválido (deve ter 5 dígitos numéricos).")

        if self.mock_mode:
            # Login aceito se código for maior que zero
            return login_code > 0

        high = (login_code >> 8) & 0xFF
        low = login_code & 0xFF
        self.send_block(self.CMD_LOGIN, [high, low])
        block = self.read_block()
        self.send_ack()
        return True

    def disconnect(self):
        """Função 06: Close Controller and Go Back."""
        if self.connected:
            try:
                self.send_block(self.CMD_END_SESSION)
            except Exception:
                pass
            self.connected = False
            if self.ser:
                try:
                    self.ser.close()
                except Exception:
                    pass
            logger.info("Sessão KW1281 encerrada com envio de comando 0x06 (Close Controller).")

    def __del__(self):
        try:
            if self.connected:
                self.disconnect()
        except Exception:
            pass
