import copy
import json
from decimal import Decimal
from pathlib import Path
import unittest

from erp_sandbox_advisor.core import analyze, amount, cash_projection, inventory_cost, ranking_score


EXAMPLE = Path(__file__).resolve().parents[1] / "data" / "examples" / "synthetic_scenario.json"


class CalculationTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads(EXAMPLE.read_text(encoding="utf-8"))

    def test_synthetic_scenario(self):
        result = analyze(self.data)
        self.assertEqual(result["cash"]["closing_cash"], "30")
        self.assertTrue(result["cash"]["safe"])
        self.assertEqual(result["ranking_score"], "34.0")
        self.assertEqual(result["inventory"]["period_penalty"], "2")
        self.assertEqual(result["inventory"]["annual_fee"], "1")
        self.assertEqual(result["orders"][0]["contribution"], "13")
        self.assertFalse(result["orders"][1]["eligible"])

    def test_cash_shortfall_before_later_receipt(self):
        result = cash_projection("5", [{"label": "purchase", "inflow": "0", "outflow": "8"},
                                       {"label": "collection", "inflow": "9", "outflow": "0"}])
        self.assertFalse(result["safe"])
        self.assertEqual(result["funding_gap"], "3")
        self.assertEqual(result["closing_cash"], "6")

    def test_empty_cash_events(self):
        self.assertEqual(cash_projection("0", [])["minimum_cash"], "0")

    def test_decimal_arithmetic(self):
        result = cash_projection("0.1", [{"label": "receipt", "inflow": "0.2", "outflow": "0"}])
        self.assertEqual(result["closing_cash"], "0.3")

    def test_nonfinite_and_invalid_numbers(self):
        for value in ("NaN", "Infinity", "-Infinity", "unknown", True, None, [], {}):
            with self.subTest(value=value), self.assertRaises(ValueError):
                amount(value, "value")

    def test_negative_cash_input(self):
        with self.assertRaises(ValueError):
            cash_projection("-1", [])

    def test_negative_event_amount(self):
        with self.assertRaises(ValueError):
            cash_projection("1", [{"label": "invalid", "inflow": "0", "outflow": "-1"}])

    def test_weights_and_ranking(self):
        self.assertEqual(ranking_score("20", "10", "0.7", "0.3"), Decimal("17"))
        with self.assertRaises(ValueError):
            ranking_score("20", "10", "0.7", "0.4")

    def test_inventory_exact_boundaries(self):
        rules = self.data["inventory_rules"]
        result = inventory_cost({"a": 4, "b": 4, "c": 2}, rules)
        self.assertEqual(result["charged_units"], 0)
        self.assertEqual(inventory_cost({"a": 2}, rules)["annual_fee"], "0")
        self.assertEqual(inventory_cost({"a": 7}, rules)["annual_fee"], "1")
        self.assertEqual(inventory_cost({"a": 8}, rules)["annual_fee"], "3")

    def test_inventory_overlap_modes(self):
        rules = self.data["inventory_rules"]
        result = inventory_cost({"a": 7, "b": 6}, rules)
        self.assertEqual(result["charged_units"], 5)
        rules["overlap"] = "add"
        self.assertEqual(inventory_cost({"a": 7, "b": 6}, rules)["charged_units"], 8)

    def test_inventory_invalid_rules(self):
        for field, value in (("overlap", "unknown"), ("total_limit", True), ("per_product_limit", -1),
                             ("penalty_per_unit", "-1"), ("annual_bands", [{"above": 2, "fee": "1"}, {"above": 1, "fee": "2"}])):
            with self.subTest(field=field), self.assertRaises(ValueError):
                rules = copy.deepcopy(self.data["inventory_rules"])
                rules[field] = value
                inventory_cost({}, rules)

    def test_each_order_blocker(self):
        for key, value, blocker in (("market", "other", "market_not_qualified"),
                                    ("product", "other", "product_not_qualified"),
                                    ("required_certifications", ["other"], "certification_missing"),
                                    ("ready_period", 3, "delivery_too_late"),
                                    ("available_units", 2, "insufficient_units")):
            with self.subTest(key=key):
                data = copy.deepcopy(self.data)
                data["orders"] = [data["orders"][0]]
                data["orders"][0][key] = value
                self.assertEqual(analyze(data)["orders"][0]["blockers"], [blocker])

    def test_loss_not_confused_with_ineligibility(self):
        self.data["orders"][0]["unit_cost"] = "20"
        order = analyze(self.data)["orders"][0]
        self.assertTrue(order["eligible"])
        self.assertFalse(order["profitable"])

    def test_duplicate_orders(self):
        self.data["orders"].append(copy.deepcopy(self.data["orders"][0]))
        with self.assertRaises(ValueError):
            analyze(self.data)

    def test_unknown_and_missing_fields(self):
        for key in ("unexpected", "company"):
            data = copy.deepcopy(self.data)
            if key == "unexpected":
                data[key] = 1
            else:
                del data[key]
            with self.assertRaises(ValueError):
                analyze(data)

    def test_invalid_quantities(self):
        for value in (0, -1, 1.5, True, "3"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.data["orders"][0]["quantity"] = value
                analyze(self.data)

    def test_schema_version(self):
        for value in (2, True, "1"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.data["schema_version"] = value
                analyze(self.data)

    def test_analysis_does_not_mutate_input(self):
        before = copy.deepcopy(self.data)
        analyze(self.data)
        self.assertEqual(self.data, before)


if __name__ == "__main__":
    unittest.main()
