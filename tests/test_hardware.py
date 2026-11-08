"""
Testes unitários para a camada de hardware, abstração serial e autodetecção de cabos.
"""

import unittest
from core.hardware import list_available_ports, find_kkl_cable_port, MockECUKLineInterface


class TestHardwareLayer(unittest.TestCase):

    def test_list_ports_callable(self):
        ports = list_available_ports()
        self.assertIsInstance(ports, list)

    def test_find_kkl_cable_port_callable(self):
        # Deve retornar dict ou None sem lançar exceções
        result = find_kkl_cable_port()
        if result is not None:
            self.assertIn("device", result)

    def test_mock_ecu_handshake(self):
        mock = MockECUKLineInterface(ecu_id="030906032")
        self.assertTrue(mock.open())
        self.assertTrue(mock.send_5baud_slow_init(0x01))
        
        sync, kb1, kb2, addr_comp = mock.simulate_handshake()
        self.assertEqual(sync, 0x55)
        self.assertEqual(kb1, 0x01)
        self.assertEqual(kb2, 0x8A)
        ack_sent = kb2 ^ 0xFF
        self.assertEqual(ack_sent, 0x75)
        self.assertEqual(addr_comp, 0xFE)

    def test_mock_measuring_blocks(self):
        mock = MockECUKLineInterface()
        block1 = mock.get_simulated_measuring_block(1)
        self.assertEqual(len(block1), 4)
        self.assertEqual(block1[0]["unit"], "RPM")
        self.assertGreater(block1[0]["value"], 800)

    def test_iso9141_odd_parity(self):
        # Validação matemática da norma ISO 9141-2 para inicialização a 5 baud
        for address in [0x01, 0x02, 0x03, 0x08, 0x15, 0x17, 0x25, 0x46]:
            data_bits = [(address >> i) & 1 for i in range(7)]
            parity = 1 - (sum(data_bits) % 2)
            total_ones = sum(data_bits) + parity
            self.assertEqual(total_ones % 2, 1, f"Falha de paridade ímpar no endereço 0x{address:02X}")


if __name__ == "__main__":
    unittest.main()
