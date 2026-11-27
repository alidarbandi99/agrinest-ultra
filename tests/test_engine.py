import unittest
from engine import analyze,normalize

class LabTests(unittest.TestCase):
    def test_farsi_digit_and_water(self):
        data=analyze("کلسیم ۳۰ mg/L\nمنیزیم ۱۴٫۴ mg/L\nEC ۰٫۴۸ dS/m\npH ۶٫۰۰","water")
        self.assertEqual(data["row_count"],4)
        self.assertEqual(data["rows"][0]["value"],30)
        self.assertEqual(data["rows"][1]["value"],14.4)
        self.assertEqual(data["rows"][2]["unit"],"dS/m")
        self.assertFalse(data["use_in_calculation_allowed"])
    def test_ions_are_not_nitrogen_basis(self):
        data=analyze("NO3 62 mg/L\nNO3-N 14 mg/L\nSO4 125 mg/L","water")
        self.assertEqual([x["key"] for x in data["rows"]],["NO3","NO3-N","SO4"])
    def test_detection_limits(self):
        data=analyze("Mn <0.01 mg/L\nFe Trace mg/L","water")
        self.assertEqual(data["rows"][0]["qualifier"],"<")
        self.assertIsNone(data["rows"][1]["value"])
        self.assertFalse(data["rows"][0]["verified"])
    def test_soil_not_directly_subtractable(self):
        data=analyze("Ca 250 mg/kg","soil")
        self.assertTrue(any("مستقیم" in w for w in data["rows"][0]["warnings"]))
    def test_ambiguous_comma_quarantined(self):
        data=analyze("Ca 1,200 mg/L")
        self.assertEqual(data["row_count"],0)
        self.assertEqual(len(data["needs_review"]),1)
    def test_duplicate(self):
        data=analyze("Ca 40 mg/L\nCa 50 mg/L")
        self.assertEqual(len(data["rows"]),2)
        self.assertTrue(data["rows"][0]["warnings"])
    def test_unknown_is_not_assumed(self):
        data=analyze("XYZ 20 mg/L\nCa 20 mg/L")
        self.assertEqual(data["row_count"],1)
        self.assertEqual(len(data["needs_review"]),1)
    def test_no_auto_approval(self):
        data=analyze("K 200 mg/L")
        self.assertFalse(data["use_in_calculation_allowed"])
        self.assertEqual(data["status"],"needs_human_review")

if __name__=="__main__": unittest.main()
