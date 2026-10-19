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
from gui.settingsDialogs import SettingsPanel, NVDASettingsDialog
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

# 推薦的輸出點字表（設定面板預設列出；NVDA+Alt+B 在勾選的表間循環）
OUTPUT_TABLES = [
    ("zh-tw.ctb",          "注音點字 (zh-tw)"),
    ("zh-tw-ueb-g1.ctb",   "注音點字 + UEB 一級"),
    ("zh-tw-ueb-g2.ctb",   "注音點字 + UEB 二級"),
    ("zh-tw-short.ctb",  "縮點閱讀"),
]

# 推薦的輸入點字表（NVDA+Alt+I 在勾選的表間循環）
INPUT_TABLES = [
    ("en-us-comp8-ext.utb", "英文電腦點字 (en-us-comp8)"),
    ("en-ueb-g1.ctb",   "UEB 一級輸入 (en-ueb-g1)"),
    ("en-ueb-g2.ctb",   "UEB 二級輸入 (en-ueb-g2)"),
]

CONF_SECTION = "brailleTableSwitcher"
# 預設勾選：升級前的三個輸出表與三個輸入表，縮點不勾
config.conf.spec[CONF_SECTION] = {
    "outputTables": 'string_list(default=list("zh-tw.ctb", "zh-tw-ueb-g1.ctb", "zh-tw-ueb-g2.ctb"))',
    "inputTables": 'string_list(default=list("en-us-comp8-ext.utb", "en-ueb-g1.ctb", "en-ueb-g2.ctb"))',
    "showAllTables": "boolean(default=False)",
}


def _tableName(tableId):
    """推薦清單裡的友善名稱，其他表用 NVDA 的 displayName。"""
    if not tableId:
        return "（未設定）"
    for tid, name in OUTPUT_TABLES + INPUT_TABLES:
        if tableId == tid:
            return name
    try:
        return getBRLtable(tableId).displayName
    except Exception:
        return tableId


def _friendlyOutputName(tableObj):
    fileName = getattr(tableObj, "fileName", None)
    return _tableName(fileName) if fileName else ("（未設定）" if tableObj is None else str(tableObj))


def _friendlyInputName(tableId):
    return _tableName(tableId)


def _cycleList(kind):
    """設定中勾選、而且 NVDA 找得到的表；全部失效時退回推薦清單的預設。"""
    key, defaults = ("outputTables", OUTPUT_TABLES[:3]) if kind == "output" else ("inputTables", INPUT_TABLES)
    ids = []
    for tid in config.conf[CONF_SECTION][key]:
        try:
            getBRLtable(tid)
            ids.append(tid)
        except LookupError:
            log.warning(f"brailleTableSwitcher: table not found, skipped: {tid}")
    return ids or [tid for tid, _ in defaults]


def _candidates(kind, showAll, checked):
    """設定面板要列出的表：推薦清單、已勾選的其他表；showAll 時再加上 NVDA 所有同類表。"""
    from brailleTables import listTables
    rec = OUTPUT_TABLES if kind == "output" else INPUT_TABLES
    ids = [tid for tid, _ in rec]
    extra = []
    for t in sorted(listTables(), key=lambda t: t.displayName):
        if t.fileName in ids or not (t.output if kind == "output" else t.input):
            continue
        if showAll or t.fileName in checked:
            extra.append(t.fileName)
    return ids + extra


class BrailleTableSwitcherPanel(SettingsPanel):
    title = "點字表切換"

    def makeSettings(self, settingsSizer):
        from gui import guiHelper, nvdaControls
        helper = guiHelper.BoxSizerHelper(self, sizer=settingsSizer)
        conf = config.conf[CONF_SECTION]
        self._checked = {"output": list(conf["outputTables"]), "input": list(conf["inputTables"])}
        self.showAllCheck = helper.addItem(wx.CheckBox(self, label="顯示所有點字表(&A)"))
        self.showAllCheck.SetValue(conf["showAllTables"])
        self.showAllCheck.Bind(wx.EVT_CHECKBOX, self._onShowAll)
        self.lists = {
            "output": helper.addLabeledControl(
                "NVDA+Alt+B 輸出點字表循環(&O)：", nvdaControls.CustomCheckListBox, choices=[]),
            "input": helper.addLabeledControl(
                "NVDA+Alt+I 輸入點字表循環(&I)：", nvdaControls.CustomCheckListBox, choices=[]),
        }
        self._ids = {}
        for kind in self.lists:
            self._fill(kind)

    def _fill(self, kind):
        lst = self.lists[kind]
        ids = _candidates(kind, self.showAllCheck.GetValue(), self._checked[kind])
        self._ids[kind] = ids
        lst.SetItems([_tableName(tid) for tid in ids])
        lst.SetCheckedItems([i for i, tid in enumerate(ids) if tid in self._checked[kind]])
        if ids:
            lst.SetSelection(0)

    def _currentChecked(self, kind):
        return [self._ids[kind][i] for i in self.lists[kind].GetCheckedItems()]

    def _onShowAll(self, evt):
        for kind in self.lists:
            self._checked[kind] = self._currentChecked(kind)
            self._fill(kind)

    def isValid(self):
        for kind, label in (("output", "輸出"), ("input", "輸入")):
            if not self._currentChecked(kind):
                gui.messageBox(f"{label}點字表至少要勾選一個。", "點字表切換", wx.OK | wx.ICON_ERROR, self)
                self.lists[kind].SetFocus()
                return False
        return super().isValid()

    def onSave(self):
        conf = config.conf[CONF_SECTION]
        conf["outputTables"] = self._currentChecked("output")
        conf["inputTables"] = self._currentChecked("input")
        conf["showAllTables"] = self.showAllCheck.GetValue()


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
        NVDASettingsDialog.categoryClasses.append(BrailleTableSwitcherPanel)

    def terminate(self):
        try:
            NVDASettingsDialog.categoryClasses.remove(BrailleTableSwitcherPanel)
        except ValueError:
            pass
        super().terminate()

    # ── 開啟設定 (NVDA+Alt+P) ────────────────────────────────────────────
    @script(
        description="開啟點字表切換設定（選擇循環的點字表）",
        category=addonHandler.getCodeAddon().manifest["summary"],
        gesture="kb:NVDA+alt+p",
    )
    def script_openSettings(self, gesture):
        wx.CallAfter(gui.mainFrame.popupSettingsDialog, NVDASettingsDialog, BrailleTableSwitcherPanel)

    # ── 輸出點字表切換 (NVDA+Alt+B) ──────────────────────────────────────
    @script(
        description="在勾選的輸出點字表間循環切換",
        category=addonHandler.getCodeAddon().manifest["summary"],
        gesture="kb:NVDA+alt+b",
    )
    def script_cycleBrailleTable(self, gesture):
        ids = _cycleList("output")
        currentId = getattr(braille.handler.table, "fileName", None)
        idx = ids.index(currentId) if currentId in ids else -1
        nextId = ids[(idx + 1) % len(ids)]

        try:
            braille.handler.table = getBRLtable(nextId)
            ui.message(_tableName(nextId))
        except Exception:
            log.error(f"brailleTableSwitcher: failed to switch output table to {nextId}", exc_info=True)
            playErrorSound()

    # ── 輸入點字表切換 (NVDA+Alt+I) ──────────────────────────────────────
    @script(
        description="在勾選的輸入點字表間循環切換",
        category=addonHandler.getCodeAddon().manifest["summary"],
        gesture="kb:NVDA+alt+i",
    )
    def script_cycleInputBrailleTable(self, gesture):
        # 輸入表存在 config，不在 braille.handler
        # 舊版 config 可能儲存已改名的 key（如 en-us-comp8.ctb），套用 RENAMED_TABLES 對應
        from brailleTables import RENAMED_TABLES
        currentId = config.conf["braille"]["inputTable"]
        currentId = RENAMED_TABLES.get(currentId, currentId)
        ids = _cycleList("input")
        idx = ids.index(currentId) if currentId in ids else -1
        nextId = ids[(idx + 1) % len(ids)]

        try:
            config.conf["braille"]["inputTable"] = nextId
            # 通知 brailleInput 模組重新讀取設定
            brailleInput.handler.table = getBRLtable(nextId)
            ui.message(_tableName(nextId))
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
