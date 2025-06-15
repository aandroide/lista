# -*- coding: utf-8 -*-
import xbmc
import xbmcgui
import xbmcaddon
import xbmcvfs
import os
import json
import urllib.request
import re
from resources.lib.utils import get_sources, download_and_extract_zip

ADDON = xbmcaddon.Addon()
ADDON_PATH = xbmcvfs.translatePath(ADDON.getAddonInfo('path'))
ELEMENTUM_REPO_ID = "repository.elementumorg"

def download_elementum_repo():
    sources = get_sources()
    elementum = next((s for s in sources if s.get("name", "").lower() == "elementum repo"), None)

    if not elementum or not elementum.get("url"):
        xbmc.log("[ElementumRepoInstaller] URL della repo Elementum non trovata in addons.json", xbmc.LOGERROR)
        xbmcgui.Dialog().notification("Elementum Repo", "URL non trovata in addons.json", xbmcgui.NOTIFICATION_ERROR, 3000)
        return False

    releases_url = elementum["url"]
    try:
        # Estrae il percorso del repository dall'URL
        repo_path = re.search(r'https://github.com/([^/]+/[^/]+)', releases_url)
        if not repo_path:
            raise Exception("URL GitHub non valido")
        
        api_url = f"https://api.github.com/repos/{repo_path.group(1)}/releases/latest"
        
        with urllib.request.urlopen(api_url, timeout=15) as response:
            release_data = json.loads(response.read().decode('utf-8'))
            assets = release_data.get("assets", [])
            
            # Cerca l'asset ZIP del repository
            zip_asset = next((a for a in assets if "repository.elementumorg" in a["name"].lower() and a["name"].endswith(".zip")), None)
            if not zip_asset:
                raise Exception("Nessun file ZIP del repository trovato")
            
            zip_url = zip_asset["browser_download_url"]
            success = download_and_extract_zip(zip_url, "Elementum Repo")
            return success
            
    except Exception as e:
        xbmc.log(f"[ElementumRepoInstaller] Errore: {str(e)}", xbmc.LOGERROR)
        xbmcgui.Dialog().notification("Elementum Repo", f"Errore: {str(e)}", xbmcgui.NOTIFICATION_ERROR, 3000)
        return False