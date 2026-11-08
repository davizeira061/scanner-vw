"""
Testes unitários completos para o motor de protocolo KW1281 cobrindo 100% das funções do VCDS-Lite.
"""

import unittest
from core.kw1281 import KW1281Engine


class TestKW1281EngineAllFeatures(unittest.TestCase):

    def setUp(self):
        self.engine = KW1281Engine(mock_mode=True, mock_ecu_type="BOSCH_MP90")
        self.engine.connect(0x01)

    def tearDown(self):
        self.engine.disconnect()

    def test_connect_and_ecu_info(self):
        self.assertTrue(self.engine.connected)
        self.assertIn("030906027", self.engine.ecu_info["part_number"])
        self.assertIn("MOTRONIC", self.engine.ecu_info["component"])

    def test_auto_identify_bosch_and_marelli(self):
        # 1. Testa Bosch MP9.0
        detected_bosch = self.engine.identify_ecu_system()
        self.assertEqual(detected_bosch["family"], "BOSCH_MP90")
        self.assertEqual(detected_bosch["recommended_tbi_mode"], 3)  # Grupo 098

        # 2. Testa Magneti Marelli 1AVP
        engine_marelli = KW1281Engine(mock_mode=True, mock_ecu_type="MARELLI_1AVP")
        engine_marelli.connect(0x01)
        detected_marelli = engine_marelli.identify_ecu_system()
        self.assertEqual(detected_marelli["family"], "MARELLI_1AVP")
        self.assertEqual(detected_marelli["recommended_tbi_mode"], 1)  # Canal 00
        engine_marelli.disconnect()

    def test_measuring_blocks(self):
        group1 = self.engine.read_measuring_group(1)
        self.assertEqual(len(group1), 4)
        self.assertEqual(group1[0]["unit"], "RPM")

    def test_read_and_clear_dtcs(self):
        dtcs = self.engine.read_dtcs()
        self.assertGreater(len(dtcs), 0)
        self.assertEqual(dtcs[0]["code"], "00515")

        cleared = self.engine.clear_dtcs()
        self.assertTrue(cleared)
        self.assertEqual(len(self.engine.read_dtcs()), 0)

    def test_basic_settings(self):
        bs = self.engine.run_basic_settings(1)
        self.assertEqual(len(bs), 4)
        # O ponto fica travado em 9.0° APMS para estroboscópio
        timing_field = [f for f in bs if "Ponto" in f["name"]][0]
        self.assertEqual(timing_field["value"], 9.0)

    def test_output_tests(self):
        actuator1 = self.engine.trigger_next_output_test()
        self.assertIsNotNone(actuator1)
        self.assertIn("Bomba", actuator1)
        actuator2 = self.engine.trigger_next_output_test()
        self.assertIn("Marcha Lenta", actuator2)

    def test_adaptation_read_and_save(self):
        val = self.engine.read_adaptation_channel(1)
        self.assertEqual(val, 128)
        saved = self.engine.save_adaptation_channel(1, 132)
        self.assertTrue(saved)
        self.assertEqual(self.engine.read_adaptation_channel(1), 132)

    def test_reset_factory_adaptations(self):
        # Canal 00 - Reset da matriz de fábrica da EEPROM
        reset_ok = self.engine.reset_factory_adaptations()
        self.assertTrue(reset_ok)
        self.assertEqual(self.engine.mock_ecu.adaptations.get(0), 0)

    def test_tba_groups_60_and_98(self):
        # Grupo 060: TBA E-Gas Drive-by-Wire
        bs60 = self.engine.run_basic_settings(60)
        self.assertEqual(len(bs60), 4)
        status_field_60 = [f for f in bs60 if "Status" in f["name"]][0]
        self.assertEqual(status_field_60["value"], "ADP. OK")

        # Grupo 098: TBA Cabo c/ Atuador (Bosch MP 9.0)
        bs98 = self.engine.run_basic_settings(98)
        self.assertEqual(len(bs98), 4)
        status_field_98 = [f for f in bs98 if "Status" in f["name"]][0]
        self.assertIn("ADP. OK", status_field_98["value"])

    def test_recode_module(self):
        recoded = self.engine.recode_module(5211, 12345)
        self.assertTrue(recoded)
        self.assertEqual(self.engine.ecu_info["coding"], "05211")
        self.assertIn("12345", self.engine.ecu_info["wsc"])

    def test_login_security_access(self):
        login_ok = self.engine.login_security_access(12233)
        self.assertTrue(login_ok)
        login_fail = self.engine.login_security_access(0)
        self.assertFalse(login_fail)

    def test_safety_interlocks_and_bounds(self):
        # 1. Marcha lenta segura (Canal 01): valores perigosos devem ser rejeitados
        with self.assertRaises(ValueError):
            self.engine.save_adaptation_channel(1, 50)  # Muito baixo (risco de apagar motor)
        with self.assertRaises(ValueError):
            self.engine.save_adaptation_channel(1, 200)  # Muito alto (risco de acelerar sozinho)

        # Valor seguro (ex: 130) deve passar
        self.assertTrue(self.engine.save_adaptation_channel(1, 130))

        # 2. Canal 00 só aceita valor 00
        with self.assertRaises(ValueError):
            self.engine.save_adaptation_channel(0, 5)

        # 3. Recode limites numéricos seguros
        with self.assertRaises(ValueError):
            self.engine.recode_module(-1)
        with self.assertRaises(ValueError):
            self.engine.recode_module(70000)


if __name__ == "__main__":
    unittest.main()
