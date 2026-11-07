"""Research demo view contract: technical truth, display quality and JavaScript syntax."""
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from agent_dashboard_ui import PAGE

class AcademicDemoViewTests(unittest.TestCase):
    def test_academic_display(self):
        self.assertIn("AI Agent Intelligence", PAGE)
        self.assertIn("Requirement Interpretation", PAGE)
        self.assertIn("Flavor Product Matching", PAGE)
        self.assertIn("Product Bundling Intelligence", PAGE)
        self.assertIn("Demand Forecasting", PAGE)
        self.assertIn("katalog evaluasi terkontrol", PAGE)
        self.assertIn("bukan transaksi pelanggan", PAGE)
        self.assertNotIn("rp0", PAGE.lower())
        self.assertNotIn("sintetis", PAGE.lower())
        self.assertIn("Technical Review Required",PAGE)
        self.assertIn('id="result"',PAGE)
        self.assertNotIn('id="output"',PAGE)

    def test_javascript_syntax(self):
        if not shutil.which("node"):
            self.skipTest("Node unavailable in test environment")
        script = PAGE.split("<script>",1)[1].split("</script>",1)[0]
        with tempfile.TemporaryDirectory(prefix="agent_demo_ui_") as directory:
            path=Path(directory)/"agent_dashboard.js"
            path.write_text(script,encoding="utf-8")
            result=subprocess.run(["node","--check",str(path)],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)

if __name__=="__main__":
    unittest.main()
