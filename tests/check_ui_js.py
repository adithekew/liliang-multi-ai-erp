"""Syntax-check the JavaScript embedded in the Python-served HTML page."""
import ast
from pathlib import Path
import re
import subprocess
import tempfile

tree=ast.parse(Path("rich_ui.py").read_text(encoding="utf-8"))
fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=="html_page")
html=ast.literal_eval(next(n for n in fn.body if isinstance(n,ast.Return)).value)
matches=re.findall(r"<script>(.*?)</script>",html,flags=re.DOTALL|re.IGNORECASE)
assert len(matches)==1,"Expected one UI script"
with tempfile.TemporaryDirectory() as tmp:
    path=Path(tmp)/"pilot_ui.js"
    path.write_text(matches[0],encoding="utf-8")
    subprocess.run(["node","--check",str(path)],check=True)
print("PASS: ERP Multi-AI UI JavaScript is valid")
