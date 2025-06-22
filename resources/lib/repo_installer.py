# resources/lib/repo_installer.py
# Modulo generico per installazione da GitHub Release o da HTML

import json
import re
import urllib.request
from urllib.parse import urljoin
import xbmc
import xbmcgui

from resources.lib.utils import get_source_url, download_and_extract_zip, log

def install_github_release(source_predicate, repo_path_extractor, asset_filter, addon_name):
    """
    - source_predicate(s: dict) -> bool
    - repo_path_extractor(url: str) -> "owner/repo" o URL API completo
    - asset_filter(name: str) -> bool
    """
    url = get_source_url(source_predicate)
    if not url:
        msg = f"URL repo {addon_name} non trovata"
        xbmc.log(f"[{addon_name}] {msg}", xbmc.LOGERROR)
        xbmcgui.Dialog().notification(addon_name, msg,
                                      xbmcgui.NOTIFICATION_ERROR, 3000)
        return False

    try:
        path = repo_path_extractor(url)
        api  = path if path.lower().startswith('http') else f"https://api.github.com/repos/{path}/releases/latest"
        with urllib.request.urlopen(api, timeout=15) as resp:
            data = json.loads(resp.read().decode('utf-8'))

        assets = data.get('assets', [])
        z = next((a for a in assets if asset_filter(a.get('name', ''))), None)
        if not z:
            raise Exception("Nessun ZIP trovato nella release")
        return download_and_extract_zip(z['browser_download_url'], addon_name)

    except Exception as e:
        log(f"{addon_name} error: {e}", xbmc.LOGERROR)
        xbmcgui.Dialog().notification(addon_name, f"Errore: {e}",
                                      xbmcgui.NOTIFICATION_ERROR, 3000)
        return False

def install_from_html(source_predicate, zip_pattern, addon_name):
    """
    - source_predicate(s: dict) -> bool
    - zip_pattern: regex per link .zip
    """
    base = get_source_url(source_predicate)
    if not base:
        msg = f"URL repo {addon_name} non trovata"
        xbmc.log(f"[{addon_name}] {msg}", xbmc.LOGERROR)
        xbmcgui.Dialog().notification(addon_name, msg,
                                      xbmcgui.NOTIFICATION_ERROR, 3000)
        return False

    try:
        with urllib.request.urlopen(base, timeout=15) as resp:
            html = resp.read().decode('utf-8')
        links = re.findall(r'href="([^"]+\.zip)"', html, re.IGNORECASE)
        matches = [l for l in links if re.search(zip_pattern, l)]
        if not matches:
            raise Exception("Nessun file ZIP corrispondente trovato")
        zip_url = urljoin(base, matches[0])
        return download_and_extract_zip(zip_url, addon_name)

    except Exception as e:
        log(f"{addon_name} HTML error: {e}", xbmc.LOGERROR)
        xbmcgui.Dialog().notification(addon_name, f"Errore: {e}",
                                      xbmcgui.NOTIFICATION_ERROR, 3000)
        return False
