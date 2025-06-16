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
from distutils.util import strtobool

ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo('id')
ADDON_NAME = ADDON.getAddonInfo('name')

ADDON_PATH = xbmcvfs.translatePath(ADDON.getAddonInfo('path'))
LOCAL_JSON = os.path.join(ADDON_PATH, 'resources', 'addons.json')
NO_TELEGRAM_IMAGE = os.path.join(ADDON_PATH, "resources", "skins", "default", "media", "no-telegram.png")


# Logger logger migliorato e retrocompatibile con il generico
#log("Errore generico", "ERROR")
#log("Errore di Kodi", xbmc.LOGERROR
def log(message, level="INFO"):
    """
    Scrive un messaggio nel log di Kodi
    level: "INFO", "WARNING", "ERROR", "DEBUG"
    """
    try:
        if strtobool(ADDON.getSetting('enable_logging')):
            level_map = {
                "INFO": xbmc.LOGINFO,
                "WARNING": xbmc.LOGWARNING,
                "ERROR": xbmc.LOGERROR,
                "DEBUG": xbmc.LOGDEBUG
            }
            if isinstance(level, str):
                level = level_map.get(level.upper(), xbmc.LOGINFO)
            xbmc.log(f"[Addon & Repo Installer] {message}", level)
    except Exception:
        pass


def get_github_config():
    """
    Restituisce l'URL completo del file addons.json su GitHub.
    """
    github_user   = ADDON.getSetting("github_user").strip() or "aandroide"
    github_repo   = ADDON.getSetting("github_repo").strip() or "lista"
    github_branch = ADDON.getSetting("github_branch").strip() or "master"
    remote_url = f"https://raw.githubusercontent.com/{github_user}/{github_repo}/{github_branch}/resources/addons.json"
    return remote_url


def get_sources():
    """
    Carica la lista sorgenti da GitHub o da file locale in fallback.
    """
    remote_url = get_github_config()
    log(f"Download addons.json: {remote_url}", "INFO")

    sources = []
    try:
        with urllib.request.urlopen(remote_url, timeout=10) as response:
            if response.getcode() == 200:
                data = json.loads(response.read().decode('utf-8'))
                sources = data.get("sources", [])
                if sources:
                    return sources
    except Exception as e:
        log(f"Errore JSON remoto: {e}", "ERROR")

    log("Uso fallback locale", "WARNING")
    if xbmcvfs.exists(LOCAL_JSON):
        try:
            with open(LOCAL_JSON, 'r', encoding='utf-8') as f:
                data = json.load(f)
                sources = data.get("sources", [])
        except Exception as e:
            log(f"Errore JSON locale: {e}", "ERROR")

    return sources


def set_addon_enabled(addon_id):
    """
    Abilita un addon installato tramite JSON-RPC.
    """
    request = {
        "jsonrpc": "2.0",
        "method": "Addons.SetAddonEnabled",
        "params": {"addonid": addon_id, "enabled": True},
        "id": 1
    }
    response = xbmc.executeJSONRPC(json.dumps(request))
    log(f"Abilitazione {addon_id}: {response}", "INFO")


def download_and_extract_zip(zip_url, addon_name=""):
    """
    Scarica ed estrae uno ZIP, abilita l'addon contenuto e mostra notifica.
    """
    try:
        zip_name = os.path.basename(zip_url)
        packages_path = xbmcvfs.translatePath("special://home/addons/packages/")
        zip_dest = os.path.join(packages_path, zip_name)
        extract_path = xbmcvfs.translatePath("special://home/addons/")

        log(f"Scaricamento ZIP: {zip_url} → {zip_dest}", "INFO")
        urllib.request.urlretrieve(zip_url, zip_dest)

        with zipfile.ZipFile(zip_dest, 'r') as zip_ref:
            top_folder = zip_ref.namelist()[0].split('/')[0]
            zip_ref.extractall(extract_path)
            log(f"Estrazione ZIP in: {extract_path}", "DEBUG")
            log(f"Addon estratto: {top_folder}", "DEBUG")

        addon_id = top_folder
        xbmc.executebuiltin('UpdateLocalAddons')
        xbmc.sleep(1000)

        if xbmc.getCondVisibility(f'System.HasAddon({addon_id})'):
            set_addon_enabled(addon_id)
            log(f"Addon abilitato: {addon_id}", "INFO")
            xbmc.executebuiltin('UpdateLocalAddons')

        if os.path.exists(zip_dest):
            os.remove(zip_dest)
            log(f"ZIP rimosso: {zip_dest}", "INFO")

        xbmcgui.Dialog().notification(addon_name or "Addon", "Installazione completata", xbmcgui.NOTIFICATION_INFO, 3000)
        return True

    except Exception as e:
        log(f"Errore installazione ZIP: {e}", "ERROR")
        xbmcgui.Dialog().notification(addon_name or "Addon", f"Errore: {e}", xbmcgui.NOTIFICATION_ERROR, 3000)
        return False


def safe_download_file(url, destination):
    """
    Scarica un file in modo sicuro usando un file temporaneo.
    """
    try:
        log(f"Inizio download sicuro da: {url}", "DEBUG")
        with urllib.request.urlopen(url, timeout=15) as response:
            if response.getcode() == 200:
                temp_file = destination + ".tmp"
                with open(temp_file, 'wb') as f:
                    shutil.copyfileobj(response, f)
                if os.path.exists(destination):
                    os.remove(destination)
                os.rename(temp_file, destination)
                log(f"File scaricato con successo in: {destination}", "INFO")
                return True
        return False
    except Exception as e:
        log(f"Errore download file: {str(e)}", "ERROR")
        return False


def get_existing_sources():
    """
    Legge la lista sorgenti attualmente presenti in sources.xml.
    """
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
        log(f"Errore lettura sources.xml: {str(e)}", "ERROR")
        return []


def remove_physical_repo(repo_id):
    """
    Rimuove fisicamente un repository dalla cartella addons/.
    """
    addons_path = xbmcvfs.translatePath("special://home/addons/")
    repo_path = os.path.join(addons_path, repo_id)
    if os.path.exists(repo_path):
        try:
            shutil.rmtree(repo_path)
            log(f"Rimossa cartella repository: {repo_path}", "INFO")
            return True
        except Exception as e:
            log(f"Errore rimozione cartella {repo_path}: {str(e)}", "ERROR")
    return False
