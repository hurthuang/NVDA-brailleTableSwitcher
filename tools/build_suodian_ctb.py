# -*- coding: utf-8 -*-
"""從 NVDA 內建的 zh-tw.ctb 產生縮點閱讀表 brailleTables/zh-tw-suodian.ctb。

縮點閱讀規則（聲母、韻母點位不變；兩者點型不重疊，字界由韻母判斷）：
  一聲不標；二聲韻母加點7；三聲韻母加點7、8；四聲韻母加點8；
  輕聲聲母加點8，沒有聲母的輕聲不標（與一聲同形）。
原表用 7／8 點區分的代名詞：他你她妳的聲母記號保留；牠祂的記號在韻母上，
會跟聲調撞在一起，維持原表寫法（含調號方）。度量衡合字（瓩、兙等）也維持原樣。

用法：python tools/build_suodian_ctb.py [zh-tw.ctb 路徑]
"""
import os
import re
import sys

SRC_DEFAULT = r"C:\Program Files\NVDA\louis\tables\zh-tw.ctb"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "brailleTables", "zh-tw-suodian.ctb")

INITIALS = {
	"135", "1234", "134", "12345",  # ㄅㄆㄇㄈ
	"145", "124", "1345", "14",  # ㄉㄊㄋㄌ
	"13", "123", "1235",  # ㄍㄎㄏ（ㄐㄑㄒ 同形）
	"1", "12", "24", "1245",  # ㄓㄔㄕㄖ
	"125", "245", "15",  # ㄗㄘㄙ
}
FINALS = {
	"123456", "12346", "12356", "1236", "12456", "1246", "1256", "126", "13456", "1346", "1356",
	"136", "1456", "146", "156", "16", "234", "2345", "23456", "2346", "235", "2356", "236",
	"2456", "246", "25", "256", "26", "34", "345", "346", "35", "356", "45", "456", "46",
}
# 國語點字調號那一方 → 聲調
TONES = {"3": 1, "2": 2, "4": 3, "5": 4, "1": 5}
CJK = re.compile(r"\\x(3[4-9A-F]|[4-9][0-9A-F])[0-9A-F]{2}", re.I)


def convert(dots):
	"""把一串「聲母-韻母-調號」點位轉成縮點閱讀；有無法解析的部分就傳回 None。"""
	cells = dots.split("-")
	out = []
	i = 0
	while i < len(cells):
		# 聲母可能帶原表區分代名詞的 7／8 點（他 1247、她 1248、你 13457、妳 13458），照樣保留
		base = cells[i].replace("7", "").replace("8", "")
		ini = cells[i] if base in INITIALS and i + 2 < len(cells) and cells[i + 1] in FINALS else None
		j = i + 1 if ini else i
		if j + 1 >= len(cells) or cells[j] not in FINALS or cells[j + 1] not in TONES:
			return None
		fin, tone = cells[j], TONES[cells[j + 1]]
		if tone == 5 and ini and "8" not in ini:
			ini += "8"
		elif tone in (2, 3, 4):
			fin += {2: "7", 3: "78", 4: "8"}[tone]
		out += [ini, fin] if ini else [fin]
		i = j + 2
	return "-".join(out)


def main():
	sys.stdout.reconfigure(encoding="utf-8")
	src = sys.argv[1] if len(sys.argv) > 1 else SRC_DEFAULT
	lines = open(src, encoding="utf-8").read().split("\n")
	out, changed, failed = [], 0, []
	for ln in lines:
		toks = ln.split(" ")
		if ln.startswith("#-display-name:"):
			ln = "#-display-name: Taiwanese bopomofo braille, Suodian (tones in dots 7-8)"
		elif ln.startswith("#-name:"):
			ln = "#-name: Taiwan zhuyin suodian"
		elif CJK.search(ln) and toks[0] in ("letter", "word", "begword") and len(toks) >= 3:
			new = convert(toks[2])
			if new is None:
				failed.append(ln)
			else:
				toks[2] = new
				ln, changed = " ".join(toks), changed + 1
		elif CJK.search(ln) and ln.startswith("noback context") and re.search(r" @[\d-]+$", ln):
			head, dots = ln.rsplit(" @", 1)
			new = convert(dots)
			if new is None:
				failed.append(ln)
			else:
				ln, changed = f"{head} @{new}", changed + 1
		out.append(ln)
	header = (
		"# 縮點閱讀表：由 NVDA-brailleTableSwitcher/tools/build_suodian_ctb.py 從 zh-tw.ctb 產生，不要手動修改\n"
		"# 一聲不標；二聲韻母加點7；三聲韻母加點7、8；四聲韻母加點8；輕聲聲母加點8（無聲母不標）\n"
	)
	with open(OUT, "w", encoding="utf-8", newline="\n") as f:
		f.write(header + "\n".join(out))
	print(f"轉換 {changed} 條，無法解析 {len(failed)} 條 → {os.path.normpath(OUT)}")
	for ln in failed[:30]:
		print("  ", ln)


if __name__ == "__main__":
	main()
