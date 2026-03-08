from logHandler import log
import config

def onUninstall():
    current = config.conf["braille"]["translationTable"]
    if current in ("zh-tw-ueb-g1.ctb", "zh-tw-ueb-g2.ctb"):
        log.info("brailleTableSwitcher: resetting translationTable to zh-tw.ctb")
        config.conf["braille"]["translationTable"] = "zh-tw.ctb"
        config.conf.save()
