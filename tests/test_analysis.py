import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import analysis


class PaymentDescriptionTests(unittest.TestCase):
    def test_mercadopago_comercialsana_is_not_treated_as_payment(self):
        self.assertFalse(analysis.is_payment_description("MERCADOPAGOCOMERCIALSANA"))

    def test_known_payment_terms_are_still_treated_as_payment(self):
        self.assertTrue(analysis.is_payment_description("PAGO PESOS TAR 1400"))
        self.assertTrue(analysis.is_payment_description("PAGO ONLINE"))


if __name__ == "__main__":
    unittest.main()
