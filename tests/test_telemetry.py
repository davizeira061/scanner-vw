"""
Testes unitários para o módulo de telemetria e exportação.
"""

import os
import unittest
import tempfile
from database.telemetry import TelemetryLogger


class TestTelemetry(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "test_telemetry.db")
        self.logger = TelemetryLogger(db_path=self.db_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_session_lifecycle_and_logging(self):
        s_id = self.logger.start_session("VW Gol G2 1.0 8v", "030906032", "1AVP", "Teste de bancada")
        self.assertIsNotNone(s_id)

        sample_fields = [
            {"name": "RPM", "value": 920.0, "unit": "RPM", "text": "920 RPM"},
            {"name": "ECT", "value": 88.0, "unit": "°C", "text": "88.0 °C"}
        ]
        self.logger.log_measuring_fields(group=1, fields=sample_fields)
        self.logger.log_dtc("00515", "Sensor Hall G40")
        self.logger.end_session()

        csv_out = os.path.join(self.temp_dir.name, "test_export.csv")
        exported = self.logger.export_session_to_csv(s_id, csv_out)
        self.assertTrue(exported)
        self.assertTrue(os.path.exists(csv_out))

        with open(csv_out, "r", encoding="utf-8") as f:
            content = f.read()
            self.assertIn("RPM", content)
            self.assertIn("920", content)


if __name__ == "__main__":
    unittest.main()
