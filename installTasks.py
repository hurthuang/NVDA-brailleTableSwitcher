from logHandler import log
import config

def onUninstall():
    current = config.conf["braille"].get("outputTable", "")
    if current in ("zh-tw-ueb-g1.ctb", "zh-tw-ueb-g2.ctb"):
        log.info("brailleTableSwitcher: resetting outputTable to zh-tw.ctb")
        config.conf["braille"]["outputTable"] = "zh-tw.ctb"
        config.conf.save()
