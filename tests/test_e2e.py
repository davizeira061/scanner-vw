"""
Teste de Integração End-to-End (E2E) do Scanner-VW (OpenVAG).
Verifica todo o pipeline operacional: Handshake, Leitura de Sensores,
Diagnóstico de Falhas, Gravação de Telemetria e Endpoints da API Web.
"""

import unittest
import urllib.request
import json
import time
from core.kw1281 import KW1281Engine
from database.dtc_db import DTCDatabase
from database.telemetry import TelemetryLogger
from ui.web_server import start_web_server


class TestEndToEndPipeline(unittest.TestCase):

    def test_full_diagnostic_pipeline(self):
        # 1. Handshake e Conexão
        engine = KW1281Engine(mock_mode=True, part_number_hint="030-906-032-AKK")
        self.assertTrue(engine.connect(0x01))
        self.assertIn("030906", engine.ecu_info["part_number"])

        # 2. Leitura de Sensores (Grupo 1)
        group1 = engine.read_measuring_group(1)
        self.assertEqual(len(group1), 4)
        rpm_val = group1[0]["value"]
        self.assertGreater(rpm_val, 800)

        # 3. Diagnóstico de Falhas
        dtcs = engine.read_dtcs()
        self.assertGreater(len(dtcs), 0)
        dtc_code = dtcs[0]["code"]

        db = DTCDatabase()
        info = db.lookup(dtc_code)
        self.assertIn("Hall", info["component"])
        self.assertGreater(len(info["multimeter_test"]), 2)

        # 4. Telemetria e Banco de Dados
        logger = TelemetryLogger()
        s_id = logger.start_session("VW Gol G2 1.0 8v", engine.ecu_info["part_number"])
        logger.log_measuring_fields(1, group1)
        logger.log_dtc(dtc_code, info["component"])
        logger.end_session()
        self.assertIsNotNone(s_id)

        # 5. Servidor Web de Telemetria
        port = 8899
        server = start_web_server(engine, port=port)
        time.sleep(0.3)

        try:
            # Testa rota de telemetria
            with urllib.request.urlopen(f"http://localhost:{port}/api/telemetry") as resp:
                self.assertEqual(resp.status, 200)
                data = json.loads(resp.read().decode())
                self.assertIn("fields", data)
                self.assertEqual(len(data["fields"]), 4)

            # Testa rota de DTCs
            with urllib.request.urlopen(f"http://localhost:{port}/api/dtcs") as resp:
                self.assertEqual(resp.status, 200)
                data = json.loads(resp.read().decode())
                self.assertIn("dtcs", data)
                self.assertGreater(len(data["dtcs"]), 0)

        finally:
            server.shutdown()
            server.server_close()
            engine.disconnect()


if __name__ == "__main__":
    unittest.main()
