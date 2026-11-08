"""
Testes unitários para o decodificador de grandezas físicas e fórmulas KW1281.
"""

import unittest
from core.sensor_decoder import KW1281SensorDecoder


class TestSensorDecoder(unittest.TestCase):

    def test_decode_rpm(self):
        # Formula 1: RPM
        res = KW1281SensorDecoder.decode_field(1, 184, 1)
        self.assertEqual(res["unit"], "RPM")
        self.assertAlmostEqual(res["value"], 36.8, delta=1.0)

    def test_decode_temperature(self):
        # Formula 5: Coolant Temp
        res = KW1281SensorDecoder.decode_field(5, 138, 0)
        self.assertEqual(res["unit"], "°C")
        self.assertEqual(res["value"], 88.0)  # 138 - 50 = 88°C

    def test_decode_battery_volts(self):
        # Formula 8: Volts
        res = KW1281SensorDecoder.decode_field(8, 140, 1)
        self.assertEqual(res["unit"], "V")
        self.assertGreater(res["value"], 1.0)

    def test_decode_1avp_group_000(self):
        # Teste com 10 bytes típicos de marcha lenta da 1AVP em temperatura operacional
        # ECT=138 (88°C), Bat=290, TPS=2 (0.8%), MAP=90 (360mbar), RPM=23 (920 RPM)
        raw = [138, 140, 2, 90, 23, 96, 92, 40, 128, 0]
        fields = KW1281SensorDecoder.decode_1avp_group_000(raw)
        self.assertEqual(len(fields), 10)
        self.assertEqual(fields[0]["name"], "Temp. Motor (ECT)")
        self.assertEqual(fields[0]["value"], 88)
        self.assertEqual(fields[4]["name"], "Rotação (RPM)")
        self.assertEqual(fields[4]["value"], 920)
        self.assertEqual(fields[3]["name"], "Pressão Coletor (MAP)")
        self.assertEqual(fields[3]["value"], 360)


if __name__ == "__main__":
    unittest.main()
