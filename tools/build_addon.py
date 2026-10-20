# -*- coding: utf-8 -*-
"""打包 brailleTableSwitcher-<版本>.nvda-addon（版本取自 manifest.ini）。

用法：python tools/build_addon.py [輸出資料夾]   （預設輸出到 repo 根目錄）
內容：manifest.ini、README.md、installTasks.py、globalPlugins/*.py、brailleTables/*.ctb
"""
import os
import re
import sys
import zipfile

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))


def main():
	sys.stdout.reconfigure(encoding="utf-8")
	manifest = open(os.path.join(ROOT, "manifest.ini"), encoding="utf-8").read()
	version = re.search(r'^version\s*=\s*"?([^"\n]+)"?', manifest, re.M).group(1).strip()
	outDir = sys.argv[1] if len(sys.argv) > 1 else ROOT
	out = os.path.join(outDir, f"brailleTableSwitcher-{version}.nvda-addon")
	files = ["manifest.ini", "README.md", "installTasks.py"]
	for sub, ext in (("globalPlugins", ".py"), ("brailleTables", ".ctb")):
		files += [f"{sub}/{f}" for f in sorted(os.listdir(os.path.join(ROOT, sub))) if f.endswith(ext)]
	with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
		for f in files:
			z.write(os.path.join(ROOT, f), f)
	print(out)
	for f in files:
		print("  ", f)


if __name__ == "__main__":
	main()
