# -*- coding: utf-8 -*-
from brailleTables import getTable as getBRLtable
from logHandler import log
from nvwave import playErrorSound
from scriptHandler import script
import addonHandler
import braille
import globalPluginHandler
import ui

addonHandler.initTranslation()

TABLES = [
    ("zh-tw.ctb",        "注音點字 (zh-tw)"),
    ("zh-tw-ueb-g1.ctb", "注音點字 + UEB 一級"),
    ("zh-tw-ueb-g2.ctb", "注音點字 + UEB 二級"),
]


class GlobalPlugin(globalPluginHandler.GlobalPlugin):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @script(
        description="循環切換輸出點字表 (zh-tw / UEB G1 / UEB G2)",
        category=addonHandler.getCodeAddon().manifest["summary"],
        gesture="kb:NVDA+alt+t",
    )
    def script_cycleBrailleTable(self, gesture):
        currentTable = braille.handler.table
        ids = [t[0] for t in TABLES]

        currentId = None
        for tid, _ in TABLES:
            try:
                if currentTable is getBRLtable(tid):
                    currentId = tid
                    break
            except Exception:
                pass

        idx = ids.index(currentId) if currentId in ids else -1
        nextIdx = (idx + 1) % len(TABLES)
        nextId, nextName = TABLES[nextIdx]

        try:
            braille.handler.table = getBRLtable(nextId)
            ui.message(nextName)
        except Exception:
            log.error(f"brailleTableSwitcher: failed to switch to {nextId}", exc_info=True)
            playErrorSound()
