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
import gui
import wx
import threading
import urllib.request
import urllib.error
import json
import re
import os
import tempfile

addonHandler.initTranslation()

GITHUB_LATEST_API = "https://api.github.com/repos/hurthuang/NVDA-brailleTableSwitcher/releases/latest"

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


# ── 檢查更新 ──────────────────────────────────────────────
def _parse_version(v):
    nums = [int(p) for p in re.findall(r'\d+', v)]
    nums += [0] * (4 - len(nums))
    return tuple(nums[:4])


def _current_version():
    try:
        return addonHandler.getCodeAddon().manifest.get("version", "0")
    except Exception:
        return "0"


def _check_update_worker(silent=False):
    """silent=True 用於開機自動檢查：沒有新版本時完全不提示，避免每次啟動都念一次。"""
    current = _current_version()
    try:
        req = urllib.request.Request(
            GITHUB_LATEST_API,
            headers={"Accept": "application/vnd.github+json", "User-Agent": "brailleTableSwitcher-update-check"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        if not silent:
            wx.CallAfter(ui.message, f"檢查更新失敗：{e}")
        return

    latest = data.get("tag_name", "").lstrip("vV")
    if _parse_version(latest) <= _parse_version(current):
        if not silent:
            wx.CallAfter(ui.message, f"目前已是最新版本（v{current}）。")
        return

    asset_url = None
    for asset in data.get("assets", []):
        if asset.get("name", "").endswith(".nvda-addon"):
            asset_url = asset.get("browser_download_url")
            break
    release_url = data.get("html_url", "https://github.com/hurthuang/NVDA-brailleTableSwitcher/releases")
    wx.CallAfter(_prompt_update, latest, current, asset_url, release_url)


def _prompt_update(latest, current, asset_url, release_url):
    """在主執行緒彈出確認對話框；使用者按是才下載並開啟安裝。"""
    if not asset_url:
        ui.browseableMessage(
            f"有新版本可更新：v{latest}（目前使用：v{current}）\n\n下載頁面：\n{release_url}",
            "brailleTableSwitcher 有新版本",
        )
        return
    result = gui.messageBox(
        f"發現新版本 v{latest}（目前使用：v{current}）。\n\n是否立即下載並安裝？",
        "brailleTableSwitcher 有新版本",
        wx.YES_NO | wx.ICON_QUESTION,
    )
    if result == wx.YES:
        ui.message("正在下載更新…")
        threading.Thread(target=_download_and_install_worker, args=(asset_url,), daemon=True).start()


def _download_and_install_worker(asset_url):
    try:
        req = urllib.request.Request(asset_url, headers={"User-Agent": "brailleTableSwitcher-update-check"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            content = resp.read()
    except Exception as e:
        wx.CallAfter(ui.message, f"下載更新失敗：{e}")
        return

    tmp_path = os.path.join(tempfile.gettempdir(), "brailleTableSwitcher-update.nvda-addon")
    try:
        with open(tmp_path, "wb") as f:
            f.write(content)
    except Exception as e:
        wx.CallAfter(ui.message, f"儲存更新檔失敗：{e}")
        return

    # 交給系統開啟，觸發 NVDA 原生的附加元件安裝確認流程
    wx.CallAfter(os.startfile, tmp_path)


class GlobalPlugin(globalPluginHandler.GlobalPlugin):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 啟動時背景自動檢查一次更新，延遲幾秒避免搶在 NVDA 啟動流程前面；有新版才提示，沒有則靜默
        wx.CallLater(5000, lambda: threading.Thread(
            target=_check_update_worker, kwargs={"silent": True}, daemon=True
        ).start())

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
