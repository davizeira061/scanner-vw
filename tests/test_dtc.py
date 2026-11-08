"""
Testes unitários para a base de conhecimento de DTCs e diagnóstico guiado.
"""

import unittest
from database.dtc_db import DTCDatabase


class TestDTCDatabase(unittest.TestCase):

    def setUp(self):
        self.db = DTCDatabase()

    def test_lookup_hall_sensor(self):
        info = self.db.lookup("00515")
        self.assertEqual(info["vag_code"], "00515")
        self.assertEqual(info["obd_code"], "P0340")
        self.assertIn("Hall", info["component"])
        self.assertGreater(len(info["multimeter_test"]), 3)

    def test_lookup_short_code(self):
        # Testa normalização 515 -> 00515
        info = self.db.lookup("515")
        self.assertEqual(info["vag_code"], "00515")

    def test_lookup_obd_code(self):
        # Testa busca reversa por P0130
        info = self.db.lookup("P0130")
        self.assertEqual(info["vag_code"], "00525")
        self.assertIn("Lambda", info["component"])

    def test_lookup_unknown(self):
        # Testa fallback seguro
        info = self.db.lookup("99999")
        self.assertEqual(info["vag_code"], "99999")
        self.assertIn("Falha VAG 99999", info["component"])

    def test_lookup_extended_dtcs(self):
        # 1. Sensor de Rotação G28 (00513)
        g28 = self.db.lookup("00513")
        self.assertEqual(g28["obd_code"], "P0321")
        self.assertIn("Rotação", g28["component"])
        self.assertGreater(len(g28["multimeter_test"]), 2)

        # 2. Imobilizador Bloqueado (17978 / P1570)
        immo = self.db.lookup("17978")
        self.assertEqual(immo["obd_code"], "P1570")
        self.assertIn("Imobilizador", immo["component"])

        # 3. Saída de Ignição Bobina 1 (00609)
        coil = self.db.lookup("00609")
        self.assertEqual(coil["obd_code"], "P1355")
        self.assertIn("Ignição", coil["component"])

        # 4. Total de falhas mapeadas >= 30
        self.assertGreaterEqual(len(self.db.database), 30)


if __name__ == "__main__":
    unittest.main()
