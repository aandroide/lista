# -*- coding: utf-8 -*-
import xbmc
import xbmcgui
import xbmcaddon
import xbmcvfs
import json
import os
import urllib.request
import zipfile
import shutil
import xml.etree.ElementTree as ET

ADDON_ID = xbmcaddon.Addon().getAddonInfo('id')

# Costanti addon
ADDON = xbmcaddon.Addon()
ADDON_PATH = xbmcvfs.translatePath(ADDON.getAddonInfo('path'))
LOCAL_JSON = os.path.join(ADDON_PATH, 'resources', 'addons.json')
NO_TELEGRAM_IMAGE = os.path.join(ADDON_PATH, "resources", "skins", "default", "media", "no-telegram.png")

# Carica la lista sorgenti da remoto (GitHub) o da file locale
def get_sources():
    github_user   = ADDON.getSetting("github_user").strip() or "aandroide"
    github_repo   = ADDON.getSetting("github_repo").strip() or "lista"
    github_branch = ADDON.getSetting("github_branch").strip() or "master"
    remote_url = f"https://raw.githubusercontent.com/{github_user}/{github_repo}/{github_branch}/resources/addons.json"

    xbmc.log(f"[Utils] Download addons.json: {remote_url}", xbmc.LOGINFO)
    sources = []
    try:
        with urllib.request.urlopen(remote_url, timeout=10) as response:
            if response.getcode() == 200:
                data = json.loads(response.read().decode('utf-8'))
                sources = data.get("sources", [])
    except Exception as e:
        xbmc.log(f"[Utils] Errore JSON remoto: {e}", xbmc.LOGERROR)

    if not sources and xbmcvfs.exists(LOCAL_JSON):
        try:
            with open(LOCAL_JSON, 'r', encoding='utf-8') as f:
                data = json.load(f)
                sources = data.get("sources", [])
        except Exception as e:
            xbmc.log(f"[Utils] Errore JSON locale: {e}", xbmc.LOGERROR)
    return sources

# Abilita un addon installato
def set_addon_enabled(addon_id):
    request = {
        "jsonrpc": "2.0",
        "method": "Addons.SetAddonEnabled",
        "params": {"addonid": addon_id, "enabled": True},
        "id": 1
    }
    response = xbmc.executeJSONRPC(json.dumps(request))
    xbmc.log(f"[Utils] Abilitazione {addon_id}: {response}", xbmc.LOGINFO)

# Scarica ed estrae un file ZIP, poi abilita l'addon contenuto
def download_and_extract_zip(zip_url, addon_name=""):
    try:
        zip_name = os.path.basename(zip_url)
        packages_path = xbmcvfs.translatePath("special://home/addons/packages/")
        zip_dest = os.path.join(packages_path, zip_name)
        extract_path = xbmcvfs.translatePath("special://home/addons/")

        xbmc.log(f"[Utils] Scaricamento ZIP: {zip_url} → {zip_dest}", xbmc.LOGINFO)
        urllib.request.urlretrieve(zip_url, zip_dest)

        with zipfile.ZipFile(zip_dest, 'r') as zip_ref:
            top_folder = zip_ref.namelist()[0].split('/')[0]
            zip_ref.extractall(extract_path)

        addon_id = top_folder
        xbmc.executebuiltin('UpdateLocalAddons')
        xbmc.sleep(1000)

        if xbmc.getCondVisibility(f'System.HasAddon({addon_id})'):
            set_addon_enabled(addon_id)
            xbmc.executebuiltin('UpdateLocalAddons')

        if os.path.exists(zip_dest):
            os.remove(zip_dest)
            xbmc.log(f"[Utils] ZIP rimosso: {zip_dest}", xbmc.LOGINFO)

        xbmcgui.Dialog().notification(addon_name or "Addon", "Installazione completata", xbmcgui.NOTIFICATION_INFO, 3000)
        return True

    except Exception as e:
        xbmc.log(f"[Utils] Errore installazione ZIP: {e}", xbmc.LOGERROR)
        xbmcgui.Dialog().notification(addon_name or "Addon", f"Errore: {e}", xbmcgui.NOTIFICATION_ERROR, 3000)
        return False

# Logger generico con prefisso addon
def log(message, level=xbmc.LOGINFO):
    xbmc.log(f"[{ADDON_ID}] {message}", level)

# Download sicuro con file temporaneo
def safe_download_file(url, destination):
    try:
        with urllib.request.urlopen(url, timeout=15) as response:
            if response.getcode() == 200:
                temp_file = destination + ".tmp"
                with open(temp_file, 'wb') as f:
                    shutil.copyfileobj(response, f)
                if os.path.exists(destination):
                    os.remove(destination)
                os.rename(temp_file, destination)
                return True
        return False
    except Exception as e:
        log(f"Errore download file: {str(e)}", xbmc.LOGERROR)
        return False

# Recupera sorgenti esistenti da sources.xml
def get_existing_sources():
    path = xbmcvfs.translatePath("special://profile/sources.xml")
    if not os.path.exists(path):
        return []
    try:
        tree = ET.parse(path)
        root = tree.getroot()
        existing_sources = []
        for source in root.findall(".//source"):
            path_elem = source.find('path')
            if path_elem is not None and path_elem.text:
                existing_sources.append(path_elem.text)
        return existing_sources
    except Exception as e:
        log(f"Errore lettura sources.xml: {str(e)}", xbmc.LOGERROR)
        return []

# Rimuove fisicamente un repository dalla cartella addons/
def remove_physical_repo(repo_id):
    addons_path = xbmcvfs.translatePath("special://home/addons/")
    repo_path = os.path.join(addons_path, repo_id)
    if os.path.exists(repo_path):
        try:
            shutil.rmtree(repo_path)
            log(f"Rimossa cartella repository: {repo_path}")
            return True
        except Exception as e:
            log(f"Errore rimozione cartella {repo_path}: {str(e)}", xbmc.LOGERROR)
    return False
