"""
Testes unitários para o parser de arquivos .LBL do VCDS.
"""

import unittest
import os
from core.lbl_parser import VCDSLabelParser


class TestLBLParser(unittest.TestCase):

    def setUp(self):
        self.parser = VCDSLabelParser()

    def test_find_label_file_real(self):
        # Testa se localiza arquivos no diretório real do VCDS-Lite se existir
        if os.path.exists(r"C:\Ross-Tech\VCDS-Lite\Labels"):
            path = self.parser.find_label_file("030-906-032-AKK")
            self.assertIsNotNone(path)
            self.assertTrue(path.lower().endswith(".lbl"))

    def test_parse_030_label(self):
        target = r"C:\Ross-Tech\VCDS-Lite\Labels\030-906-032-AKK.lbl"
        if os.path.exists(target):
            parsed = self.parser.parse_label_file(target)
            self.assertIn(1, parsed["groups"])
            # Grupo 1, Campo 1 deve ser Rotação / Engine Speed
            field1 = parsed["groups"][1]["fields"][1]
            self.assertIn("Engine Speed", field1["name"])
            self.assertIn("RPM", field1["spec"])


if __name__ == "__main__":
    unittest.main()
