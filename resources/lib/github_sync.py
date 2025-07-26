import os
import json
import urllib.request
import urllib.error
import xbmc
import xbmcaddon
import xbmcvfs
import xbmcgui
from .version_utils import log_info, log_error

ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo('id')
ADDON_NAME = ADDON.getAddonInfo('name')
PROFILE_PATH = xbmcvfs.translatePath(ADDON.getAddonInfo('profile'))
LAST_COMMIT_FILE = os.path.join(PROFILE_PATH, 'last_commit.txt')
ADDON_PATH = xbmcvfs.translatePath(os.path.join('special://home/addons', ADDON_ID))
IGNORE_FILES = {'.firstrun'}

# Impostazioni GitHub
github_user = ADDON.getSetting('github_user')
github_repo = ADDON.getSetting('github_repo')
github_branch = ADDON.getSetting('github_branch') or 'main'

def handle_http_error(e):
    """Gestione avanzata errori HTTP"""
    if e.code == 403:
        xbmcgui.Dialog().notification(
            ADDON_NAME,
            "Limite richieste GitHub raggiunto!",
            xbmcgui.NOTIFICATION_ERROR,
            7000
        )
        xbmcgui.Dialog().ok(
            ADDON_NAME,
            "Errore 403: Accesso negato\n\n"
            "Hai superato il limite di richieste a GitHub.\n\n"
            "Soluzioni possibili:\n"
            "1. Riavvia il modem per ottenere un nuovo IP\n"
            "2. Prova di nuovo tra 1-2 ore\n"
            "3. Contatta il provider se il problema persiste"
        )
    elif e.code == 404:
        xbmcgui.Dialog().notification(
            ADDON_NAME,
            "URL non trovato! Verifica le impostazioni",
            xbmcgui.NOTIFICATION_ERROR,
            5000
        )
    else:
        xbmcgui.Dialog().notification(
            ADDON_NAME,
            f"Errore {e.code} durante l'accesso a GitHub",
            xbmcgui.NOTIFICATION_ERROR,
            5000
        )
    return False

def github_api_request(path, timeout=10):
    """Chiamata alle API GitHub"""
    url = f"https://api.github.com/repos/{github_user}/{github_repo}{path}"
    try:
        resp = urllib.request.urlopen(url, timeout=timeout)
        if resp.getcode() != 200:
            log_error(f"API code inaspettato {resp.getcode()} per {url}")
            return None
        return json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        return handle_http_error(e)
    except Exception as e:
        log_error(f"richiesta API fallita {url}: {e}")
    return None

def read_last_commit():
    """Legge l'ultimo commit memorizzato localmente"""
    try:
        if os.path.exists(LAST_COMMIT_FILE):
            with open(LAST_COMMIT_FILE, 'r') as f:
                return f.read().strip()
    except Exception as e:
        log_error(f"lettura ultimo commit: {e}")
    return ''

def write_last_commit(sha):
    """Salva lo SHA del commit corrente"""
    try:
        with open(LAST_COMMIT_FILE, 'w') as f:
            f.write(sha)
    except Exception as e:
        log_error(f"scrittura ultimo commit: {e}")

def get_remote_commit():
    """Ottiene l'ultimo commit SHA dal ramo remoto"""
    data = github_api_request(f"/commits/{github_branch}")
    return data.get('sha', '') if data else ''

def get_remote_file_list():
    """Ottiene la lista dei file dal repository remoto"""
    data = github_api_request(f"/git/trees/{github_branch}?recursive=1")
    if not data:
        return []
    return [item['path'] for item in data.get('tree', []) if item.get('type') == 'blob']

def download_content(rel_path):
    """Scarica il contenuto di un file"""
    url = f"https://raw.githubusercontent.com/{github_user}/{github_repo}/{github_branch}/{rel_path}"
    try:
        with urllib.request.urlopen(url, timeout=20) as response:
            return response.read()
    except urllib.error.HTTPError as e:
        handle_http_error(e)
    except Exception as e:
        log_error(f"Errore download {rel_path}: {e}")
    return None

def sync_orphan_files(remote_paths):
    """Rimuove i file locali non presenti nel remoto"""
    for root, _, files in os.walk(ADDON_PATH, topdown=False):
        for name in files:
            full_path = os.path.join(root, name)
            rel_path = os.path.relpath(full_path, ADDON_PATH).replace('\\', '/')
            
            if rel_path in IGNORE_FILES:
                continue
                
            if rel_path not in remote_paths:
                try:
                    os.remove(full_path)
                    log_info(f"Rimosso file orfano: {rel_path}")
                except Exception as e:
                    log_error(f"Errore rimozione file orfano {rel_path}: {e}")
        
        if not os.listdir(root) and root != ADDON_PATH:
            try:
                os.rmdir(root)
                log_info(f"Rimossa cartella vuota: {os.path.relpath(root, ADDON_PATH)}")
            except Exception as e:
                log_error(f"Errore rimozione cartella vuota: {e}")

def sync_all(remote_paths):
    """Sincronizza tutti i file con il repository remoto"""
    for rel_path in remote_paths:
        local_path = os.path.join(ADDON_PATH, rel_path)
        remote_content = download_content(rel_path)
        
        if remote_content is None:
            continue
            
        file_exists = os.path.exists(local_path)
        if file_exists:
            try:
                with open(local_path, 'rb') as local_file:
                    if local_file.read() == remote_content:
                        continue
            except Exception as e:
                log_error(f"Errore lettura file locale {rel_path}: {e}")
        
        try:
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            with open(local_path, 'wb') as local_file:
                local_file.write(remote_content)
            log_info(f"File {'aggiornato' if file_exists else 'scaricato'}: {rel_path}")
        except Exception as e:
            log_error(f"Errore scrittura file {rel_path}: {e}")
    
    sync_orphan_files(remote_paths)
