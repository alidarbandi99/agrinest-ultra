import unittest
from eye import normalize, parse_text

class TestAgrinestEye(unittest.TestCase):
    def test_persian_digits(self):
        self.assertEqual(normalize("۲۲۰٫۵"), "220.5")

    def test_water_extraction(self):
        report = parse_text("Ca: 220 mg/L\nMg: 81.6 mg/L\nEC: 1.1 dS/m\npH 7.34", "water")
        self.assertEqual(report["measurements"]["ca"][0]["value"], 220)
        self.assertEqual(report["measurements"]["mg"][0]["value"], 81.6)
        self.assertEqual(report["measurements"]["ec"][0]["unit_original"], "dS/m")
        self.assertFalse(report["review_required"])

    def test_soil_and_missing_unit(self):
        report = parse_text("فسفر: 12 mg/kg\nکلسیم: 200", "soil")
        self.assertEqual(report["measurements"]["p"][0]["value"], 12)
        self.assertTrue(report["review_required"])

    def test_duplicate_detection(self):
        report = parse_text("Ca: 12 mg/L\nCa: 14 mg/L", "water")
        self.assertTrue(report["review_required"])
        self.assertEqual(len(report["measurements"]["ca"]), 2)

    def test_not_guessing_absent_elements(self):
        report = parse_text("Ca: 220 mg/L", "water")
        self.assertNotIn("mg", report["measurements"])

    def test_reject_ambiguous_comma(self):
        report = parse_text("Ca: 1,200 mg/L", "water")
        self.assertNotIn("ca", report["measurements"])
        self.assertTrue(report["review_required"])

if __name__ == "__main__":
    unittest.main()
