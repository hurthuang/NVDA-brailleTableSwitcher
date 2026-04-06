# -*- coding: utf-8 -*-
from brailleTables import getTable as getBRLtable
from logHandler import log
from nvwave import playErrorSound
from scriptHandler import script
import addonHandler
import braille
import brailleInput
import config
import globalPluginHandler
import ui

addonHandler.initTranslation()

# 輸出點字表清單（NVDA+Alt+B 循環切換）
OUTPUT_TABLES = [
    ("zh-tw.ctb",        "注音點字 (zh-tw)"),
    ("zh-tw-ueb-g1.ctb", "注音點字 + UEB 一級"),
    ("zh-tw-ueb-g2.ctb", "注音點字 + UEB 二級"),
]

# 輸入點字表清單（NVDA+Alt+I 循環切換）
INPUT_TABLES = [
    ("en-us-comp8-ext.utb", "英文電腦點字 (en-us-comp8)"),
    ("en-ueb-g1.ctb",   "UEB 一級輸入 (en-ueb-g1)"),
    ("en-ueb-g2.ctb",   "UEB 二級輸入 (en-ueb-g2)"),
]


def _friendlyOutputName(tableObj):
    """從輸出表清單查友善名稱，找不到則回退到 displayName。"""
    if tableObj is None:
        return "（未設定）"
    for tid, name in OUTPUT_TABLES:
        try:
            if tableObj is getBRLtable(tid):
                return name
        except Exception:
            pass
    return getattr(tableObj, "displayName", str(tableObj))


def _friendlyInputName(tableId):
    """從輸入表清單查友善名稱，找不到則直接傳回 tableId。"""
    if not tableId:
        return "（未設定）"
    for tid, name in INPUT_TABLES:
        if tableId == tid:
            return name
    # 回退：嘗試從 NVDA 表資料庫取 displayName
    try:
        return getBRLtable(tableId).displayName
    except Exception:
        return tableId


class GlobalPlugin(globalPluginHandler.GlobalPlugin):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    # ── 輸出點字表切換 (NVDA+Alt+B) ──────────────────────────────────────
    @script(
        description="循環切換輸出點字表 (zh-tw / UEB G1 / UEB G2)",
        category=addonHandler.getCodeAddon().manifest["summary"],
        gesture="kb:NVDA+alt+b",
    )
    def script_cycleBrailleTable(self, gesture):
        currentTable = braille.handler.table
        ids = [t[0] for t in OUTPUT_TABLES]

        currentId = None
        for tid, _ in OUTPUT_TABLES:
            try:
                if currentTable is getBRLtable(tid):
                    currentId = tid
                    break
            except Exception:
                pass

        idx = ids.index(currentId) if currentId in ids else -1
        nextIdx = (idx + 1) % len(OUTPUT_TABLES)
        nextId, nextName = OUTPUT_TABLES[nextIdx]

        try:
            braille.handler.table = getBRLtable(nextId)
            ui.message(nextName)
        except Exception:
            log.error(f"brailleTableSwitcher: failed to switch output table to {nextId}", exc_info=True)
            playErrorSound()

    # ── 輸入點字表切換 (NVDA+Alt+I) ──────────────────────────────────────
    @script(
        description="循環切換輸入點字表 (en-us-comp8 / UEB G1 / UEB G2)",
        category=addonHandler.getCodeAddon().manifest["summary"],
        gesture="kb:NVDA+alt+i",
    )
    def script_cycleInputBrailleTable(self, gesture):
        # 輸入表存在 config，不在 braille.handler
        # 舊版 config 可能儲存已改名的 key（如 en-us-comp8.ctb），套用 RENAMED_TABLES 對應
        from brailleTables import RENAMED_TABLES
        currentId = config.conf["braille"]["inputTable"]
        currentId = RENAMED_TABLES.get(currentId, currentId)
        ids = [t[0] for t in INPUT_TABLES]

        idx = ids.index(currentId) if currentId in ids else -1
        nextIdx = (idx + 1) % len(INPUT_TABLES)
        nextId, nextName = INPUT_TABLES[nextIdx]

        try:
            config.conf["braille"]["inputTable"] = nextId
            # 通知 brailleInput 模組重新讀取設定
            brailleInput.handler.table = getBRLtable(nextId)
            ui.message(nextName)
        except Exception:
            log.error(f"brailleTableSwitcher: failed to switch input table to {nextId}", exc_info=True)
            playErrorSound()

    # ── 報讀當前輸出與輸入轉譯表 (NVDA+Alt+O) ────────────────────────────
    @script(
        description="報讀當前輸出與輸入點字轉譯表",
        category=addonHandler.getCodeAddon().manifest["summary"],
        gesture="kb:NVDA+alt+o",
    )
    def script_announceBrailleTables(self, gesture):
        try:
            outputName = _friendlyOutputName(braille.handler.table)
            inputId    = config.conf["braille"]["inputTable"]
            inputName  = _friendlyInputName(inputId)
            ui.message(f"輸出：{outputName}；輸入：{inputName}")
        except Exception:
            log.error("brailleTableSwitcher: failed to announce tables", exc_info=True)
            playErrorSound()
