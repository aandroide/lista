# -*- coding: utf-8 -*-
import xbmc
import xbmcgui
import xbmcaddon
import xbmcvfs
import os
import json
import urllib.request
from resources.lib.utils import get_sources, download_and_extract_zip

ADDON = xbmcaddon.Addon()
ADDON_PATH = xbmcvfs.translatePath(ADDON.getAddonInfo('path'))

def download_sandmann_repo():
    sources = get_sources()
    sandmann = next((s for s in sources if "sandmann79" in s.get("name", "").lower() and "amazon" in s.get("name", "").lower()), None)

    if not sandmann or not sandmann.get("url"):
        xbmc.log("[SandmannRepoInstaller] URL della repo Sandmann non trovata in addons.json", xbmc.LOGERROR)
        xbmcgui.Dialog().notification("Sandmann Repo", "URL non trovata in addons.json", xbmcgui.NOTIFICATION_ERROR, 3000)
        return

    release_url = sandmann["url"]
    try:
        with urllib.request.urlopen(release_url, timeout=10) as response:
            release_data = json.loads(response.read().decode('utf-8'))
            assets = release_data.get("assets", [])
            if not assets:
                raise Exception("Nessun file ZIP trovato nella release.")
            zip_url = assets[0]["browser_download_url"]
    except Exception as e:
        xbmc.log(f"[SandmannRepoInstaller] Errore parsing JSON GitHub: {e}", xbmc.LOGERROR)
        xbmcgui.Dialog().notification("Sandmann Repo", f"Errore nel recupero ZIP: {e}", xbmcgui.NOTIFICATION_ERROR, 3000)
        return

    download_and_extract_zip(zip_url, "Sandmann Repo")
