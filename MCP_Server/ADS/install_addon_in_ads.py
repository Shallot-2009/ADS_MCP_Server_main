"""Run this file from the ADS Python console once to register the live addon."""

from pathlib import Path

from keysight.ads.de import app


ADDON_NAME = "ADS Codex MCP Live Bridge"
ADDON_INIT = Path(__file__).resolve().parent / "ads_live_bridge" / "__init__.py"

existing = app.find_addon(ADDON_NAME)
if existing is not None:
    app.remove_user_addon(existing)

addon = app.Addon(ADDON_NAME, str(ADDON_INIT), enabled=True, location=app.AddonLocale.USER)
addon.root_directory = str(ADDON_INIT.parent.parent)
app.add_user_addon(addon)
app.enable_addon(addon, True)
print(f"Installed and enabled: {ADDON_NAME}")
print(f"Source: {ADDON_INIT}")
