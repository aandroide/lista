# resources/lib/repo_installer.py
# Modulo completo per gestione repository
# -*- coding: utf-8 -*-

import json
import re
import urllib.request
import xbmc
import xbmcgui
import traceback
from urllib.parse import urljoin

from resources.lib.utils import (
    get_source_url,
    download_and_extract_zip,
    log,
    get_existing_sources,
    remove_physical_repo
)
from resources.lib.sources_manager import add_source_to_xml, remove_source_from_xml

# ID repository speciali
KODINERDS_REPO_ID = "repository.kodinerds"
SANDMANN_REPO_ID = "repository.sandmann79.plugins"
ELEMENTUM_REPO_ID = "repository.elementumorg"
IAGL_REPO_ID = "repository.zachmorris"


# ------------------------------------------------------------
# VERIFICA REPO INSTALLATI
# ------------------------------------------------------------

def is_repo_installed(repo):
    """Controlla se un repository è installato"""
    name = repo.get("name", "").lower()
    url = repo.get("url", "")

    if "kodinerds" in name:
        return xbmc.getCondVisibility(f"System.HasAddon({KODINERDS_REPO_ID})") == 1

    if "sandmann" in name:
        return xbmc.getCondVisibility(f"System.HasAddon({SANDMANN_REPO_ID})") == 1

    if "elementum" in name:
        return xbmc.getCondVisibility(f"System.HasAddon({ELEMENTUM_REPO_ID})") == 1

    # IAGL – Zac Morris
    if ("iagl" in name or
        "zach" in name or
        "morris" in name or
        "zachmorris" in name):
        return xbmc.getCondVisibility(f"System.HasAddon({IAGL_REPO_ID})") == 1

    # Altri: controlla sources.xml
    return url in get_existing_sources()


# ------------------------------------------------------------
# INSTALLA REPO
# ------------------------------------------------------------

def install_repo(repo):
    """Installa un singolo repository"""
    name = repo['name']
    lower = name.lower()

    try:
        if "kodinerds" in lower:
            from resources.lib.kodinerds_downloader import download_latest_kodinerds_zip
            return download_latest_kodinerds_zip()

        elif "sandmann" in lower:
            from resources.lib.sandmann_repo_installer import download_sandmann_repo
            return download_sandmann_repo()

        elif "elementum" in lower:
            from resources.lib.elementum_repo_installer import download_elementum_repo
            return download_elementum_repo()

        # --- INSTALLAZIONE ZAC MORRIS (come Sandmann, ZIP diretto)
        elif ("iagl" in lower or
              "zach" in lower or
              "morris" in lower or
              "zachmorris" in lower):
            from resources.lib.zacmorris_repo_installer import download_zacmorris_repo
            return download_zacmorris_repo()

        # Default → aggiunta a sources.xml
        else:
            return add_source_to_xml(repo)

    except Exception:
        log(f"Errore install {name}: {traceback.format_exc()}", xbmc.LOGERROR)
        return False


# ------------------------------------------------------------
# DISINSTALLA REPO
# ------------------------------------------------------------

def uninstall_repo(repo):
    """Disinstalla un singolo repository"""
    name = repo['name']
    lower = name.lower()

    try:
        if "kodinerds" in lower:
            return remove_physical_repo(KODINERDS_REPO_ID)

        elif "sandmann" in lower:
            return remove_physical_repo(SANDMANN_REPO_ID)

        elif "elementum" in lower:
            return remove_physical_repo(ELEMENTUM_REPO_ID)

        # --- DISINSTALLA ZAC MORRIS
        elif ("iagl" in lower or
              "zach" in lower or
              "morris" in lower or
              "zachmorris" in lower):
            return remove_physical_repo(IAGL_REPO_ID)

        else:
            return remove_source_from_xml(repo)

    except Exception:
        log(f"Errore uninstall {name}: {traceback.format_exc()}", xbmc.LOGERROR)
        return False


# ------------------------------------------------------------
# INSTALLA TUTTI I REPO
# ------------------------------------------------------------

def install_all_repos(sources, progress_callback=None):
    added = skipped = 0
    total = len(sources)

    for i, repo in enumerate(sources):
        if progress_callback and progress_callback(i, total, repo['name']):
            break

        if is_repo_installed(repo):
            skipped += 1
            continue

        if install_repo(repo):
            added += 1
        else:
            skipped += 1

    return added, skipped


# ------------------------------------------------------------
# DISINSTALLA TUTTI I REPO
# ------------------------------------------------------------

def uninstall_all_repos(sources, progress_callback=None):
    removed = errors = 0
    total = len(sources)

    for i, repo in enumerate(sources):
        if progress_callback and progress_callback(i, total, repo['name']):
            break

        if not is_repo_installed(repo):
            continue

        if uninstall_repo(repo):
            removed += 1
        else:
            errors += 1

    return removed, errors


# ------------------------------------------------------------
# INSTALLAZIONE GENERICA GITHUB
# ------------------------------------------------------------

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

        api = path if path.lower().startswith('http') \
            else f"https://api.github.com/repos/{path}/releases/latest"

        with urllib.request.urlopen(api, timeout=15) as resp:
            data = json.loads(resp.read().decode('utf-8'))

        assets = data.get("assets", [])
        z = next((a for a in assets if asset_filter(a.get("name", ""))), None)

        if not z:
            raise Exception("Nessun ZIP trovato nella release")

        return download_and_extract_zip(z["browser_download_url"], addon_name)

    except Exception as e:
        log(f"{addon_name} error: {e}", xbmc.LOGERROR)
        xbmcgui.Dialog().notification(addon_name, f"Errore: {e}",
                                      xbmcgui.NOTIFICATION_ERROR, 3000)
        return False


# ------------------------------------------------------------
# INSTALLAZIONE DA HTML
# ------------------------------------------------------------

def install_from_html(source_predicate, zip_pattern, addon_name):
    base = get_source_url(source_predicate)
    if not base:
        msg = f"URL repo {addon_name} non trovata"
        xbmc.log(f"[{addon_name}] {msg}", xbmc.LOGERROR)
        xbmcgui.Dialog().notification(addon_name, msg,
                                      xbmcgui.NOTIFICATION_ERROR, 3000)
        return False

    try:
        with urllib.request.urlopen(base, timeout=15) as resp:
            html = resp.read().decode("utf-8")

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
