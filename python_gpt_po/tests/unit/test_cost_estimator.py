import os
import shutil
import unittest

import polib

from python_gpt_po.utils.cost_estimator import CostEstimator


class TestCostEstimatorMinimal(unittest.TestCase):
    def setUp(self):
        self.test_dir = os.path.abspath("test_cost_est_minimal")
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
        os.makedirs(self.test_dir)

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_minimal_token_math(self):
        """Verify tokenize once and multiply by languages."""
        po_path = os.path.join(self.test_dir, "test.po")
        po = polib.POFile()
        # "Hello" is approx 1-2 tokens.
        po.append(polib.POEntry(msgid="Hello", msgstr=""))
        po.save(po_path)

        # 1 language
        est1 = CostEstimator.estimate_cost(self.test_dir, ["fr"], "gpt-4o-mini")
        t1 = est1['total_tokens']

        # 3 languages
        est3 = CostEstimator.estimate_cost(self.test_dir, ["fr", "es", "de"], "gpt-4o-mini")
        t3 = est3['total_tokens']
        
        self.assertEqual(t3, t1 * 3)

    def test_pricing_lookup(self):
        """Verify dynamic pricing lookup via genai-prices."""
        po_path = os.path.join(self.test_dir, "test.po")
        po = polib.POFile()
        po.append(polib.POEntry(msgid="Test", msgstr=""))
        po.save(po_path)

        # Known model
        est_known = CostEstimator.estimate_cost(self.test_dir, ["fr"], "gpt-4o-mini")
        self.assertIsNotNone(est_known['estimated_cost'])

        # Unknown model
        est_unknown = CostEstimator.estimate_cost(self.test_dir, ["fr"], "unknown-model")
        self.assertIsNone(est_unknown['estimated_cost'])

    def test_zero_work(self):
        """Verify zero tokens when everything is translated."""
        po_path = os.path.join(self.test_dir, "test.po")
        po = polib.POFile()
        po.append(polib.POEntry(msgid="Hello", msgstr="Bonjour"))
        po.save(po_path)

        est = CostEstimator.estimate_cost(self.test_dir, ["fr"], "gpt-4o-mini")
        self.assertEqual(est['total_tokens'], 0)


if __name__ == '__main__':
    unittest.main()
