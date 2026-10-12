import ast
import re
from pathlib import Path

tree=ast.parse(Path("rich_ui.py").read_text(encoding="utf-8"))
fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=="html_page")
html=ast.literal_eval(next(n for n in fn.body if isinstance(n,ast.Return)).value)
scripts=re.findall(r"<script>(.*?)</script>",html,flags=re.DOTALL|re.IGNORECASE)
assert len(scripts)==1,"Expected one inline UI script"
Path("/tmp/liliang_ui_ci.js").write_text(scripts[0],encoding="utf-8")
print("Extracted JavaScript for syntax check")
