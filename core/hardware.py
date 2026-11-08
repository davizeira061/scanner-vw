"""
Módulo de abstração de hardware e comunicação serial para o cabo KKL (CH341 / FTDI).
Suporta portas seriais reais (via pyserial), detecção automática de conexão (Hotplug)
e simulação completa para testes (MockSerial).
"""

import time
import logging
from typing import List, Optional, Tuple, Dict, Any

try:
    import serial
    import serial.tools.list_ports
    HAS_SERIAL = True
except ImportError:
    HAS_SERIAL = False

logger = logging.getLogger("scanner_vw.hardware")


def list_available_ports() -> List[Dict[str, str]]:
    """
    Lista todas as portas seriais disponíveis no Windows, identificando
    possíveis cabos KKL baseados nos chips CH340, CH341 ou FTDI.
    """
    if not HAS_SERIAL:
        return []

    ports_info = []
    for port in serial.tools.list_ports.comports():
        is_kkl = False
        desc = (port.description or "").lower()
        hwid = (port.hwid or "").lower()

        # VID 1A86 = WCH (CH340/CH341), VID 0403 = FTDI (FT232R)
        if "1a86" in hwid or "0403" in hwid or "ch34" in desc or "usb-serial" in desc or "kkl" in desc:
            is_kkl = True

        ports_info.append({
            "device": port.device,
            "description": port.description,
            "hwid": port.hwid,
            "is_likely_kkl": is_kkl
        })
    return ports_info


def find_kkl_cable_port() -> Optional[Dict[str, Any]]:
    """
    Varre as portas do sistema e retorna automaticamente a porta do cabo KKL se conectado.
    Retorna None se nenhum cabo compatível for detectado.
    """
    ports = list_available_ports()
    # 1. Procura por cabo reconhecido com alta probabilidade
    for p in ports:
        if p["is_likely_kkl"]:
            return p

    # 2. Se houver apenas 1 porta serial USB no computador, assume-se como o cabo
    usb_ports = [p for p in ports if "usb" in (p["description"] or "").lower() or "usb" in (p["hwid"] or "").lower()]
    if len(usb_ports) == 1:
        return usb_ports[0]

    return None


class KLineSerialInterface:
    """
    Interface de comunicação para Linha K (ISO 9141 / KW1281).
    Lida com bit-banging a 5 baud, ajustes de temporização e purga de eco.
    """

    def __init__(self, port: str = "COM4", baudrate: int = 9600, timeout: float = 1.0):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.ser: Optional[serial.Serial] = None
        self.is_open = False
        self.echo_mismatch_count = 0

    def open(self) -> bool:
        if not HAS_SERIAL:
            raise RuntimeError("Biblioteca pyserial não instalada.")
        try:
            self.ser = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=self.timeout,
                write_timeout=self.timeout
            )
            self.is_open = True
            self.echo_mismatch_count = 0
            self.purge()
            logger.info("Porta serial %s aberta com sucesso a %d bps.", self.port, self.baudrate)
            return True
        except Exception as e:
            logger.error("Falha ao abrir porta serial %s: %s", self.port, e)
            self.is_open = False
            raise

    def close(self):
        if self.ser and self.ser.is_open:
            try:
                self.ser.break_condition = False
            except Exception:
                pass
            self.ser.close()
        self.is_open = False
        logger.info("Porta serial fechada.")

    def purge(self):
        if self.ser and self.ser.is_open:
            self.ser.reset_input_buffer()
            self.ser.reset_output_buffer()

    def set_baudrate(self, baud: int):
        if self.ser and self.ser.is_open:
            self.ser.baudrate = baud
            self.baudrate = baud

    def send_5baud_slow_init(self, address: int = 0x01) -> bool:
        """
        Gera a inicialização lenta a 5 bauds (200ms por bit) utilizando bit-banging
        através da Break Condition no pino Tx.
        Garante que a linha K nunca seja mantida em nível lógico baixo (break) mesmo em caso de erro.
        """
        if not self.ser or not self.ser.is_open:
            raise RuntimeError("Porta serial fechada.")

        logger.info("Disparando 5-baud Slow Init no endereço 0x%02X...", address)
        self.purge()

        bit_duration = 0.200  # 200 ms por bit

        data_bits = [(address >> i) & 1 for i in range(7)]
        # ISO 9141-2: Paridade estritamente ÍMPAR (Odd Parity: sum(data_bits) + parity deve ser ímpar)
        parity = 1 - (sum(data_bits) % 2)

        frame = [0] + data_bits + [parity, 1]

        try:
            for bit in frame:
                if bit == 0:
                    self.ser.break_condition = True
                else:
                    self.ser.break_condition = False
                time.sleep(bit_duration)
        finally:
            # Trava de segurança: NUNCA deixa a linha em break condition
            self.ser.break_condition = False

        time.sleep(0.050)

        self.set_baudrate(self.baudrate)
        self.purge()
        return True

    def write_byte(self, b: int) -> None:
        if not self.ser or not self.ser.is_open:
            raise RuntimeError("Porta serial fechada.")
        data = bytes([b & 0xFF])
        self.ser.write(data)
        self.ser.flush()

        echo = self.ser.read(1)
        if not echo:
            self.echo_mismatch_count += 1
            logger.warning("Timeout aguardando eco do byte 0x%02X na Linha K (falhas: %d)", b, self.echo_mismatch_count)
            if self.echo_mismatch_count >= 5:
                raise RuntimeError("Falha de comunicação na Linha K: Sem retorno de eco do cabo KKL. Verifique conexão USB e alimentação 12V da tomada OBD2.")
        elif echo[0] != b:
            self.echo_mismatch_count += 1
            logger.warning("Aviso de eco desalinhado: enviado 0x%02X, recebido 0x%02X (falhas: %d)", b, echo[0], self.echo_mismatch_count)
            if self.echo_mismatch_count >= 5:
                raise RuntimeError("Falha de integridade na Linha K: Eco incompatível contínuo. Possível curto-circuito ou colisão de dados no barramento.")
        else:
            self.echo_mismatch_count = 0

    def read_byte(self, timeout: Optional[float] = None) -> Optional[int]:
        if not self.ser or not self.ser.is_open:
            raise RuntimeError("Porta serial fechada.")

        old_timeout = self.ser.timeout
        if timeout is not None:
            self.ser.timeout = timeout

        b = self.ser.read(1)

        if timeout is not None:
            self.ser.timeout = old_timeout

        if b:
            return b[0]
        return None


class MockECUKLineInterface:
    """
    Emulador completo de ECU K-Line (suporta Bosch Motronic MP 9.0, Bosch ME 7.x e Magneti Marelli 1AVP).
    Suporta todos os serviços do VCDS-Lite: ID, Medições, Falhas, Atuadores, Adaptação, Codificação e Login.
    """

    def __init__(self, ecu_id: Optional[str] = None, component: Optional[str] = None, coding: Optional[str] = None, ecu_type: str = "BOSCH_MP90"):
        self.ecu_type = ecu_type
        if ecu_type == "MARELLI_1AVP":
            self.ecu_id = ecu_id or "030906032CP"
            self.component = component or "1.0l R4/2V 1AVP  0001"
            self.coding = coding or "04211"
        else:
            # Padrão: Bosch Motronic MP 9.0 do Gol Mi 1.0 8v
            self.ecu_id = ecu_id or "030906027AA"
            self.component = component or "1.0l R4/2V MOTRONIC MP9.0"
            self.coding = coding or "00000"

        self.wsc = "WSC 00000"
        self.is_open = False
        self.synchronized = False
        self.block_counter = 0

        # Estado dos sensores
        self.rpm = 920.0
        self.coolant_temp = 88.0
        self.battery_volts = 13.85
        self.tps_angle = 0.8
        self.map_mbar = 360.0
        self.lambda_volts = 0.450
        self.timing_angle = 9.0

        # Falhas simuladas (DTCs)
        self.dtcs = ["00515", "00525"]

        # Canais de Adaptação simulados
        self.adaptations = {
            1: 128,  # Ajuste de Marcha Lenta (128 = 920 RPM padrão)
            2: 128,  # Enriquecimento de Partida
            3: 128,  # Adaptação de Aceleração
            4: 128,  # Ajuste de Ignição Global
        }

        # Sequência de Teste de Atuadores (Output Tests)
        self.output_tests = [
            "Relé da Bomba de Combustível (J17)",
            "Válvula de Controle da Marcha Lenta (N71)",
            "Válvula de Purga do Cânister (N80)",
            "Válvula Injetora Cilindro 1 (N30)",
            "Válvula Injetora Cilindro 2 (N31)",
            "Válvula Injetora Cilindro 3 (N32)",
            "Válvula Injetora Cilindro 4 (N33)",
            "Tacômetro / Ponteiro de RPM (Painel)"
        ]
        self.current_output_idx = 0

    def open(self) -> bool:
        self.is_open = True
        self.synchronized = False
        return True

    def close(self):
        self.is_open = False
        self.synchronized = False

    def purge(self):
        pass

    def set_baudrate(self, baud: int):
        pass

    def send_5baud_slow_init(self, address: int = 0x01) -> bool:
        self.synchronized = False
        self.block_counter = 0
        return True

    def simulate_handshake(self) -> Tuple[int, int, int, int]:
        return 0x55, 0x01, 0x8A, 0xFE

    def get_simulated_measuring_block(self, group: int) -> List[Dict[str, Any]]:
        import random
        rpm_jitter = self.rpm + random.uniform(-15, 15)
        lambda_jitter = max(0.1, min(0.9, self.lambda_volts + random.uniform(-0.15, 0.15)))

        if group == 1:
            return [
                {"name": "Rotação do Motor", "value": round(rpm_jitter, 1), "unit": "RPM", "min": 850, "max": 950},
                {"name": "Temperatura ECT", "value": round(self.coolant_temp, 1), "unit": "°C", "min": 80, "max": 105},
                {"name": "Sonda Lambda", "value": round(lambda_jitter, 3), "unit": "V", "min": 0.1, "max": 0.9},
                {"name": "Ponto de Ignição", "value": round(self.timing_angle, 1), "unit": "° APMS", "min": 6.0, "max": 12.0}
            ]
        elif group == 2:
            return [
                {"name": "Rotação do Motor", "value": round(rpm_jitter, 1), "unit": "RPM", "min": 850, "max": 950},
                {"name": "Pressão Coletor (MAP)", "value": round(self.map_mbar, 1), "unit": "mbar", "min": 280, "max": 420},
                {"name": "Abertura TPS", "value": round(self.tps_angle, 1), "unit": "%", "min": 0.0, "max": 4.0},
                {"name": "Tensão da Bateria", "value": round(self.battery_volts, 2), "unit": "V", "min": 13.2, "max": 14.5}
            ]
        elif group == 3:
            return [
                {"name": "Rotação do Motor", "value": round(rpm_jitter, 1), "unit": "RPM", "min": 850, "max": 950},
                {"name": "Tempo de Injeção", "value": 3.45, "unit": "ms", "min": 2.5, "max": 4.5},
                {"name": "Ar de Admissão", "value": 28.5, "unit": "°C", "min": 15, "max": 50},
                {"name": "Velocidade", "value": 0, "unit": "km/h", "min": 0, "max": 180}
            ]
        elif group == 60:
            return [
                {"name": "Sensor 1 TPS (G187)", "value": 14.2, "unit": "%", "min": 3.0, "max": 93.0},
                {"name": "Sensor 2 TPS (G188)", "value": 85.8, "unit": "%", "min": 97.0, "max": 3.0},
                {"name": "Contador Passos", "value": 8, "unit": "steps", "min": 0, "max": 8},
                {"name": "Status Alinhamento", "value": "ADP. OK", "unit": "", "min": 0, "max": 0}
            ]
        elif group == 98:
            return [
                {"name": "Potenciômetro TPS 1 (G69)", "value": 4.15, "unit": "V", "min": 0.5, "max": 4.9},
                {"name": "Posicionador Marcha Lenta (G88)", "value": 3.85, "unit": "V", "min": 0.5, "max": 4.9},
                {"name": "Posição Borboleta", "value": "LEERLAUF", "unit": "", "min": 0, "max": 0},
                {"name": "Status Alinhamento TBA", "value": "I.O. (ADP. OK)", "unit": "", "min": 0, "max": 0}
            ]
        else:
            return [
                {"name": f"Sensor {i+1}", "value": 0.0, "unit": "N/A", "min": 0, "max": 0}
                for i in range(4)
            ]

    def next_output_test(self) -> Optional[str]:
        if self.current_output_idx < len(self.output_tests):
            actuator = self.output_tests[self.current_output_idx]
            self.current_output_idx += 1
            return actuator
        self.current_output_idx = 0
        return None
