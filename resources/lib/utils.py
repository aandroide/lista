# resources/lib/utils.py
# Utility per gestione centralizzata delle sorgenti (JSON, dati, URL)

import xbmc
import xbmcgui
import xbmcaddon
import xbmcvfs
import json
import os
import urllib.request
import shutil
import zipfile
import xml.etree.ElementTree as ET

ADDON    = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo('id')
ADDON_PATH = xbmcvfs.translatePath(ADDON.getAddonInfo('path'))
LOCAL_JSON = os.path.join(ADDON_PATH, 'resources', 'addons.json')

def fetch_addons_json():
    """1) Scarica o legge il JSON completo di addons.json."""
    github_user   = ADDON.getSetting("github_user").strip() or "aandroide"
    github_repo   = ADDON.getSetting("github_repo").strip() or "lista"
    github_branch = ADDON.getSetting("github_branch").strip() or "master"
    remote_url = f"https://raw.githubusercontent.com/{github_user}/{github_repo}/{github_branch}/resources/addons.json"

    xbmc.log(f"[Utils] Fetch JSON: {remote_url}", xbmc.LOGINFO)
    data = {}
    try:
        with urllib.request.urlopen(remote_url, timeout=10) as resp:
            if resp.getcode() == 200:
                data = json.loads(resp.read().decode('utf-8'))
    except Exception as e:
        xbmc.log(f"[Utils] Errore JSON remoto: {e}", xbmc.LOGERROR)

    if not data and xbmcvfs.exists(LOCAL_JSON):
        try:
            with open(LOCAL_JSON, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            xbmc.log(f"[Utils] Errore JSON locale: {e}", xbmc.LOGERROR)
    return data

def get_sources_list():
    """2) Restituisce soltanto la lista `sources` dal JSON."""
    return fetch_addons_json().get('sources', [])

def get_source(predicate):
    """3) Trova la prima sorgente che soddisfa il `predicate`."""
    return next((s for s in get_sources_list() if predicate(s)), None)

def get_source_url(predicate):
    """4) Estrae direttamente l’URL di una singola sorgente."""
    src = get_source(predicate)
    return src.get('url') if src else None

def set_addon_enabled(addon_id):
    """Abilita un addon già installato via JSON-RPC."""
    req = {
        "jsonrpc":"2.0","method":"Addons.SetAddonEnabled",
        "params":{"addonid":addon_id,"enabled":True},"id":1
    }
    resp = xbmc.executeJSONRPC(json.dumps(req))
    xbmc.log(f"[Utils] Abilita {addon_id}: {resp}", xbmc.LOGINFO)

def download_and_extract_zip(zip_url, addon_name=""):
    """
    Scarica un .zip, lo estrae in special://home/addons/,
    abilita l’addon e notifica l’utente.
    """
    try:
        zip_name   = os.path.basename(zip_url)
        packages   = xbmcvfs.translatePath("special://home/addons/packages/")
        dest       = os.path.join(packages, zip_name)
        extract_to = xbmcvfs.translatePath("special://home/addons/")

        xbmc.log(f"[Utils] Scarica ZIP: {zip_url}", xbmc.LOGINFO)
        urllib.request.urlretrieve(zip_url, dest)
        with zipfile.ZipFile(dest, 'r') as z:
            top = z.namelist()[0].split('/')[0]
            z.extractall(extract_to)

        addon_id = top
        xbmc.executebuiltin('UpdateLocalAddons')
        xbmc.sleep(500)
        if xbmc.getCondVisibility(f"System.HasAddon({addon_id})"):
            set_addon_enabled(addon_id)
            xbmc.executebuiltin('UpdateLocalAddons')
        os.remove(dest)
        xbmcgui.Dialog().notification(addon_name or addon_id, "Installazione completata",
                                    xbmcgui.NOTIFICATION_INFO, 3000)
        return True
    except Exception as e:
        xbmc.log(f"[Utils] Errore ZIP: {e}", xbmc.LOGERROR)
        xbmcgui.Dialog().notification(addon_name or "Addon", f"Errore: {e}",
                                      xbmcgui.NOTIFICATION_ERROR, 3000)
        return False

def log(message, level=xbmc.LOGINFO):
    """Wrapper per il log con prefisso addon."""
    xbmc.log(f"[{ADDON_ID}] {message}", level)

def safe_download_file(url, dest):
    """Scarica file in modo 'sicuro', usando tmp + rename."""
    try:
        with urllib.request.urlopen(url, timeout=10) as r:
            if r.getcode() == 200:
                tmp = dest + ".tmp"
                with open(tmp, 'wb') as f:
                    shutil.copyfileobj(r, f)
                if os.path.exists(dest): os.remove(dest)
                os.rename(tmp, dest)
                return True
    except Exception as e:
        log(f"Errore download: {e}", xbmc.LOGERROR)
    return False

def get_existing_sources():
    """Legge i path già presenti in special://profile/sources.xml."""
    path = xbmcvfs.translatePath("special://profile/sources.xml")
    if not os.path.exists(path):
        return []
    try:
        tree = ET.parse(path)
        root = tree.getroot()
        urls = []
        for src in root.findall('.//source'):
            p = src.find('path')
            if p is not None and p.text:
                urls.append(p.text)
        return urls
    except Exception as e:
        log(f"Errore sources.xml: {e}", xbmc.LOGERROR)
        return []

def remove_physical_repo(repo_id):
    """Rimuove fisicamente la cartella di un repo in addons/."""
    addons = xbmcvfs.translatePath("special://home/addons/")
    p = os.path.join(addons, repo_id)
    if os.path.exists(p):
        try:
            shutil.rmtree(p)
            log(f"Rimosso repo: {p}")
            return True
        except Exception as e:
            log(f"Errore rimozione: {e}", xbmc.LOGERROR)
    return False

def remove_source_from_xml(repo):
    sources_path = xbmcvfs.translatePath("special://profile/sources.xml")
    url = repo.get("url","")
    if not os.path.exists(sources_path) or not url:
        return False
    try:
        tree = ET.parse(sources_path)
        root = tree.getroot()
        files = root.find("files")
        if files is None:
            return False
        removed = False
        for s in files.findall("source"):
            p = s.find("path")
            if p is not None and p.text == url:
                files.remove(s)
                removed = True
                break
        if removed:
            tree.write(sources_path, encoding='utf-8', xml_declaration=True)
            return True
        return False
    except Exception as e:
        log(f"Errore rimozione sources.xml: {e}", xbmc.LOGERROR)
        return False