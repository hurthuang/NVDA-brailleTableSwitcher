# -*- coding: utf-8 -*-
"""從 NVDA 內建的 zh-tw.ctb 產生縮點閱讀表 brailleTables/zh-tw-short.ctb。

縮點閱讀規則（聲母、韻母點位不變；兩者點型不重疊，字界由韻母判斷）：
  一聲不標；二聲韻母加點7；三聲韻母加點7、8；四聲韻母加點8；輕聲聲母加點8。
  沒有聲母的一聲、輕聲字不縮，保留調號方：只剩一個韻母方時會和標點同形（因 ⠹ 與「？」⠹⠀、
  啊啊 與「》」⠜⠜），一聲和輕聲也分不出來（呀、壓）。
原表用 7／8 點區分的代名詞：他你她妳的聲母記號保留；牠祂的記號在韻母上，
會跟聲調撞在一起，維持原表寫法（含調號方）。度量衡合字（瓩、兙等）也維持原樣。

多音字修正：tools/zh-polyphone-rules.json（取自 vi-tools 文字轉點字的多音字補充規則，逐條以萌典查證）
轉成整詞規則（noback always）加在表尾，蓋過 zh-tw.ctb 讀錯的地方（例：記得、值得的「得」是輕聲）。
同一份修正也產生 brailleTables/zh-tw-fix.ctb（zh-tw.ctb＋完整寫法的修正），給游標所在字展開用，
展開時看到的讀音才會和縮點一致。

用法：python tools/build_short_ctb.py [zh-tw.ctb 路徑]
"""
import json
import os
import re
import sys

SRC_DEFAULT = r"C:\Program Files\NVDA\louis\tables\zh-tw.ctb"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "brailleTables", "zh-tw-short.ctb")
OUT_FIX = os.path.join(HERE, "..", "brailleTables", "zh-tw-fix.ctb")
POLYPHONE = os.path.join(HERE, "zh-polyphone-rules.json")

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
		if not ini and tone in (1, 5):
			out += [fin, cells[j + 1]]   # 沒有聲母的一聲、輕聲：不縮
			i = j + 2
			continue
		if tone == 5 and ini and "8" not in ini:
			ini += "8"
		elif tone in (2, 3, 4):
			fin += {2: "7", 3: "78", 4: "8"}[tone]
		out += [ini, fin] if ini else [fin]
		i = j + 2
	return "-".join(out)


def syllables(dots):
	"""把一串點位切成音節（聲母?-韻母-調號）；切不開傳回 None。"""
	cells = dots.split("-")
	out = []
	i = 0
	while i < len(cells):
		base = cells[i].replace("7", "").replace("8", "")
		ini = base in INITIALS and i + 2 < len(cells) and cells[i + 1] in FINALS
		j = i + 1 if ini else i
		if j + 1 >= len(cells) or cells[j] not in FINALS or cells[j + 1] not in TONES:
			return None
		out.append("-".join(cells[i:j + 2]))
		i = j + 2
	return out


def polyphoneRules(letters):
	"""多音字修正 → [(整詞, 完整點位)]。letters：國字 → zh-tw.ctb 的字表點位（保留代名詞的 7／8 點用）。"""
	rules = []
	for r in json.load(open(POLYPHONE, encoding="utf-8")):
		text = r["text"]
		dots = "-".join("".join(str(k + 1) for k in range(8) if (ord(c) - 0x2800) >> k & 1) or "0" for c in r["braille"])
		syls = syllables(dots)
		if not syls or len(syls) != len(text):
			print("   略過（點字和字數對不上）：", text)
			continue
		for i, ch in enumerate(text):
			# 補充規則是六點寫法；和字表只差 7／8 點（代名詞記號）時用字表的寫法
			d = letters.get(ch)
			if d and d.replace("7", "").replace("8", "") == syls[i]:
				syls[i] = d
		rules.append((text, "-".join(syls)))
	return rules


def esc(text):
	return "".join(f"\\x{ord(c):04X}" for c in text)


def main():
	sys.stdout.reconfigure(encoding="utf-8")
	src = sys.argv[1] if len(sys.argv) > 1 else SRC_DEFAULT
	lines = open(src, encoding="utf-8").read().split("\n")
	out, changed, failed = [], 0, []
	letters = {}
	for ln in lines:
		toks = ln.split(" ")
		if toks[0] == "letter" and len(toks) >= 3 and CJK.fullmatch(toks[1]):
			letters.setdefault(chr(int(toks[1][2:], 16)), toks[2])
		if ln.startswith("#-display-name:"):
			ln = "#-display-name: Taiwanese bopomofo braille, short form (tones in dots 7-8)"
		elif ln.startswith("#-name:"):
			ln = "#-name: Taiwan bopomofo short"
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
		"# 縮點閱讀表：由 NVDA-brailleTableSwitcher/tools/build_short_ctb.py 從 zh-tw.ctb 產生，不要手動修改\n"
		"# 一聲不標；二聲韻母加點7；三聲韻母加點7、8；四聲韻母加點8；輕聲聲母加點8；沒有聲母的一聲、輕聲字不縮\n"
	)
	rules = polyphoneRules(letters)
	note = "# 多音字修正（tools/zh-polyphone-rules.json，取自 vi-tools 文字轉點字，萌典查證）：整詞規則蓋過原表的讀音"
	short = [f"noback always {esc(t)} {convert(d)}" for t, d in rules]
	with open(OUT, "w", encoding="utf-8", newline="\n") as f:
		f.write(header + "\n".join(out) + "\n\n" + note + "\n" + "\n".join(short) + "\n")
	with open(OUT_FIX, "w", encoding="utf-8", newline="\n") as f:
		f.write(
			"# 注音點字＋多音字修正：由 NVDA-brailleTableSwitcher/tools/build_short_ctb.py 產生，不要手動修改\n"
			"# 給縮點閱讀的游標所在字展開用，展開時的讀音才會和縮點一致\n"
			"#-index-name: Mandarin, Taiwan, bopomofo, polyphone fixes\n"
			"#-display-name: Taiwanese bopomofo braille with polyphone fixes\n"
			"include zh-tw.ctb\n\n" + note + "\n"
			+ "\n".join(f"noback always {esc(t)} {d}" for t, d in rules) + "\n")
	print(f"轉換 {changed} 條，無法解析 {len(failed)} 條，多音字修正 {len(rules)} 條 → {os.path.normpath(OUT)}")
	print(f"完整寫法的多音字修正 → {os.path.normpath(OUT_FIX)}")
	for ln in failed[:30]:
		print("  ", ln)


if __name__ == "__main__":
	main()
