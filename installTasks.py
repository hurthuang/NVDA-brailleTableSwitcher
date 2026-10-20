from logHandler import log
import config

# 本附加元件附帶的輸出表；解除安裝後 NVDA 找不到這些表會退回「自動」（可能選到英文表），所以先切回注音點字
ADDON_TABLES = ("zh-tw-ueb-g1.ctb", "zh-tw-ueb-g2.ctb", "zh-tw-short.ctb")


def onUninstall():
    # NVDA 的輸出表設定名稱是 translationTable（1.2.0 以前誤寫成 outputTable，從沒生效）
    current = config.conf["braille"]["translationTable"]
    if current in ADDON_TABLES:
        log.info(f"brailleTableSwitcher: resetting translationTable {current} to zh-tw.ctb")
        config.conf["braille"]["translationTable"] = "zh-tw.ctb"
        config.conf.save()
