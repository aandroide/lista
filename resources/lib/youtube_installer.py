# -*- coding: utf-8 -*-
"""
Plugin YouTube Installer
Scarica la release .zip del plugin.video.youtube (official o beta)
nella cartella 'special://profile/addon_data/youtube_install',
e la rende visibile in Kodi in Installa da file zip.
"""

import re
import json
import urllib.request
import xbmc
import xbmcgui
import xbmcaddon
import xbmcvfs
import os
import traceback
from resources.lib.utils import get_source_url, log
from resources.lib import sources_manager

ADDON = xbmcaddon.Addon()
ADDON_NAME = ADDON.getAddonInfo('name')

def install_youtube_addon(use_beta=False):
    """
    Scarica lo zip (official o beta) in special://profile/addon_data/youtube_install
    e registra tale cartella in sources.xml se non già presente.
    """
    try:
        base = get_source_url(lambda s: 'youtube' in s.get('name', '').lower())
        if not base:
            raise Exception("URL repository YouTube non trovata")

        urls = get_latest_youtube_urls(base)
        zip_url = urls['beta'] if use_beta else urls['official']
        if not zip_url:
            raise Exception(f"Nessun asset {'beta' if use_beta else 'official'} trovato")

        # Percorso virtuale scelto
        virtual_path = "special://profile/addon_data/youtube_install"
        dest_dir = xbmcvfs.translatePath(virtual_path)
        xbmcvfs.mkdirs(dest_dir)

        # Registra cartella come fonte visibile usando sources_manager
        fake_repo = {
            "name": "YouTube Install",
            "url": virtual_path + '/'
        }
        sources_manager.add_source_to_xml(fake_repo)

        zip_name = os.path.basename(zip_url)
        dest_path = os.path.join(dest_dir, zip_name)

        # Se esiste già, notifico e ritorno
        if os.path.exists(dest_path):
            xbmcgui.Dialog().ok(
                "YouTube Addon",
                f"Il file esiste già:\n[COLOR yellow]{zip_name}[/COLOR]\n\n"
            )
            return False

        # Scarica ZIP
        with urllib.request.urlopen(zip_url) as response:
            if response.getcode() != 200:
                raise Exception(f"Errore nel download: {response.getcode()}")
            with open(dest_path, 'wb') as f:
                f.write(response.read())

        xbmcgui.Dialog().ok(
            "YouTube Addon",
            f"File scaricato:\n[COLOR yellow]{zip_name}[/COLOR]\n\n"
            "Dopo il riavvio vai su:\n"
            "[COLOR lime]Add-on → Installa da file zip → YouTube Install[/COLOR]"
        )

        return True

    except Exception:
        log(f"YouTubeInstaller error: {traceback.format_exc()}", xbmc.LOGERROR)
        xbmcgui.Dialog().notification(
            "YouTube Addon",
            "Errore durante il download, guarda log",
            xbmcgui.NOTIFICATION_ERROR,
            5000
        )
        return False


def get_latest_youtube_urls(base=None):
    """
    Restituisce gli URL zip delle ultime release: {'official': ..., 'beta': ...}
    """
    if base is None:
        base = get_source_url(lambda s: 'youtube' in s.get('name', '').lower())
    if not base:
        raise Exception("URL repository YouTube non trovata")

    if 'api.github.com' not in base:
        m = re.search(r'https?://github\.com/([^/]+/[^/]+)', base)
        if not m:
            raise Exception(f"URL GitHub non valido: {base}")
        base = f"https://api.github.com/repos/{m.group(1)}/releases"

    try:
        with urllib.request.urlopen(base, timeout=15) as resp:
            if resp.getcode() != 200:
                raise Exception(f"Errore API GitHub: {resp.getcode()}")
            releases = json.loads(resp.read().decode('utf-8'))
    except Exception as e:
        raise Exception(f"Errore richiesta JSON: {e}")

    releases = releases if isinstance(releases, list) else [releases]
    official_url, beta_url = None, None

    for rel in releases:
        for a in rel.get("assets", []):
            name = a["name"].lower()
            if name.endswith(".zip") and "leia" not in name and "unofficial" not in name:
                if "+beta." in name and not beta_url:
                    beta_url = a["browser_download_url"]
                elif "+beta." not in name and not official_url:
                    official_url = a["browser_download_url"]
        if official_url and beta_url:
            break

    return {
        "official": official_url.replace('%2B', '+').strip().rstrip('/') if official_url else None,
        "beta": beta_url.replace('%2B', '+').strip().rstrip('/') if beta_url else None
    }
