import unittest
from datetime import date,timedelta
from research.forecast_validation import rolling_origin_evaluate

class RollingOriginTests(unittest.TestCase):
    def points(self,n=24):
        start=date(2025,1,6)
        return [(start+timedelta(weeks=i),float(20+i)) for i in range(n)]
    def test_requires_24_contiguous_weeks(self):
        with self.assertRaisesRegex(ValueError,"24 contiguous"):
            rolling_origin_evaluate(self.points(23))
    def test_expanding_window_metrics_compare_baselines(self):
        result=rolling_origin_evaluate(self.points(24))
        self.assertEqual(result["origins"],9)
        self.assertIn("RIDGE_AR4",result["models"])
        self.assertIn("MOVING_AVERAGE_4",result["models"])
        self.assertIn("LAST_WEEK_NAIVE",result["models"])
        self.assertFalse(result["scientific_validation"])
    def test_rejects_missing_week(self):
        p=self.points()
        p.pop(10)
        with self.assertRaisesRegex(ValueError,"contiguous"):
            rolling_origin_evaluate(p)

if __name__=="__main__":unittest.main()
