# -*- coding: utf-8 -*-
import xbmc
import xbmcgui
import xbmcaddon
import xbmcvfs
import os
import json
import re
import urllib.request
from urllib.parse import urljoin
from resources.lib.utils import get_sources, download_and_extract_zip

ADDON = xbmcaddon.Addon()
ADDON_PATH = xbmcvfs.translatePath(ADDON.getAddonInfo('path'))

def download_latest_kodinerds_zip():
    sources = get_sources()
    kodinerds = next((s for s in sources if s.get("name", "").lower() == "kodinerds repo"), None)

    if not kodinerds or not kodinerds.get("url"):
        xbmc.log("[KodinerdsDownloader] URL della repo Kodinerds non trovata in addons.json", xbmc.LOGERROR)
        xbmcgui.Dialog().notification("Kodinerds", "URL non trovata in addons.json", xbmcgui.NOTIFICATION_ERROR, 3000)
        return

    base_url = kodinerds["url"]
    xbmc.log(f"[KodinerdsDownloader] URL base repo Kodinerds: {base_url}", xbmc.LOGINFO)

    try:
        with urllib.request.urlopen(base_url, timeout=15) as response:
            html = response.read().decode("utf-8")
        zip_links = re.findall(r'href="([^"]+\.zip)"', html)
        xbmc.log(f"[KodinerdsDownloader] Trovati {len(zip_links)} file .zip nella pagina HTML", xbmc.LOGINFO)
    except Exception as e:
        xbmc.log(f"[KodinerdsDownloader] Errore caricamento HTML repo: {e}", xbmc.LOGERROR)
        xbmcgui.Dialog().notification("Kodinerds", f"Errore caricamento HTML: {e}", xbmcgui.NOTIFICATION_ERROR, 3000)
        return

    full_links = [urljoin(base_url, z) for z in zip_links if "repository.kodinerds" in z]
    if not full_links:
        xbmc.log("[KodinerdsDownloader] Nessun file ZIP 'repository.kodinerds' trovato.", xbmc.LOGERROR)
        xbmcgui.Dialog().notification("Kodinerds", "Nessuno zip trovato", xbmcgui.NOTIFICATION_ERROR, 3000)
        return

    zip_url = full_links[0]
    download_and_extract_zip(zip_url, "Kodinerds")
