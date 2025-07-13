# -*- coding: utf-8 -*-
"""
Service Self-Update per Kodi addon: sincronizza i file remoti
- Esegue sync solo se c'è un nuovo commit
- Scarica file mancanti o modificati
- Rimuove file locali non più remoti
- Notifica solo se ci sono aggiornamenti, mostrando il commit
- Pulizia automatica delle installazioni temporanee
"""

import xbmc
import xbmcaddon
import xbmcvfs
import urllib.request
import json
import os
import xbmcgui
import shutil
from resources.lib import sources_manager

# Impostazioni addon
ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo('id')
ADDON_NAME = ADDON.getAddonInfo('name')
ICON_PATH = xbmcvfs.translatePath(
    os.path.join('special://home/addons', ADDON_ID, ADDON.getAddonInfo('icon'))
)

# Percorsi
PROFILE_PATH = xbmcvfs.translatePath(ADDON.getAddonInfo('profile'))
if not os.path.exists(PROFILE_PATH):
    os.makedirs(PROFILE_PATH, exist_ok=True)
LAST_COMMIT_FILE = os.path.join(PROFILE_PATH, 'last_commit.txt')
ADDON_PATH = xbmcvfs.translatePath(os.path.join('special://home/addons', ADDON_ID))

# File da preservare anche se non presenti su GitHub
IGNORE_FILES = {'.firstrun'}

# Impostazioni GitHub
github_user = ADDON.getSetting('github_user')
github_repo = ADDON.getSetting('github_repo')
github_branch = ADDON.getSetting('github_branch') or 'main'

def read_last_commit():
    try:
        if os.path.exists(LAST_COMMIT_FILE):
            with open(LAST_COMMIT_FILE, 'r') as f:
                return f.read().strip()
    except Exception as e:
        xbmc.log(f"[ServiceSelfUpdate] Errore lettura ultimo commit: {e}", xbmc.LOGERROR)
    return ''

def write_last_commit(sha):
    try:
        with open(LAST_COMMIT_FILE, 'w') as f:
            f.write(sha)
    except Exception as e:
        xbmc.log(f"[ServiceSelfUpdate] Errore scrittura ultimo commit: {e}", xbmc.LOGERROR)

def get_remote_commit():
    """
    Restituisce lo SHA dell'ultimo commit sul branch remoto.
    """
    api_url = f"https://api.github.com/repos/{github_user}/{github_repo}/commits/{github_branch}"
    try:
        with urllib.request.urlopen(api_url, timeout=10) as resp:
            if resp.getcode() != 200:
                xbmc.log(f"[ServiceSelfUpdate] Commit API code: {resp.getcode()}", xbmc.LOGERROR)
                return ''
            data = json.loads(resp.read().decode('utf-8'))
            return data.get('sha', '')
    except Exception as e:
        xbmc.log(f"[ServiceSelfUpdate] Errore fetch commit: {e}", xbmc.LOGERROR)
    return ''

def get_remote_file_list():
    """
    Restituisce la lista di tutti i file (blob) nel ramo remoto.
    """
    api_tree = f"https://api.github.com/repos/{github_user}/{github_repo}/git/trees/{github_branch}?recursive=1"
    try:
        with urllib.request.urlopen(api_tree, timeout=10) as resp:
            if resp.getcode() != 200:
                xbmc.log(f"[ServiceSelfUpdate] Tree API code: {resp.getcode()}", xbmc.LOGERROR)
                return []
            data = json.loads(resp.read().decode('utf-8'))
            return [item['path'] for item in data.get('tree', []) if item.get('type') == 'blob']
    except Exception as e:
        xbmc.log(f"[ServiceSelfUpdate] Errore Tree API: {e}", xbmc.LOGERROR)
    return []

def sync_orphan_files(remote_paths):
    """
    Rimuove i file locali che non sono più presenti nel repository remoto.
    """
    addon_real = ADDON_PATH
    for root, dirs, files in os.walk(addon_real, topdown=False):
        for name in files:
            fullpath = os.path.join(root, name)
            relpath = os.path.relpath(fullpath, addon_real).replace('\\', '/')
            if relpath in IGNORE_FILES:
                continue
            if relpath not in remote_paths:
                try:
                    os.remove(fullpath)
                    xbmc.log(f"[ServiceSelfUpdate] Rimosso orphan: {relpath}", xbmc.LOGINFO)
                except Exception as e:
                    xbmc.log(f"[ServiceSelfUpdate] Errore rimozione orphan {relpath}: {e}", xbmc.LOGERROR)
        if not os.listdir(root):
            try:
                os.rmdir(root)
            except Exception:
                pass

def sync_all(remote_paths):
    """
    Sincronizza tutti i file remoti con quelli locali:
    - Scarica file mancanti o modificati
    - Poi rimuove gli orfani
    """
    base_url = f"https://raw.githubusercontent.com/{github_user}/{github_repo}/{github_branch}"
    addon_real = ADDON_PATH
    for rel in remote_paths:
        phys = os.path.join(addon_real, rel)
        url = f"{base_url}/{rel}"
        try:
            with urllib.request.urlopen(url, timeout=20) as r:
                content = r.read()
        except Exception as e:
            xbmc.log(f"[ServiceSelfUpdate] Errore fetch {rel}: {e}", xbmc.LOGERROR)
            continue
        # verifica esistenza e differenze
        write = True
        if os.path.exists(phys):
            try:
                with open(phys, 'rb') as f:
                    if f.read() == content:
                        write = False
            except Exception:
                write = True
        if write:
            os.makedirs(os.path.dirname(phys), exist_ok=True)
            try:
                with open(phys, 'wb') as f:
                    f.write(content)
                xbmc.log(f"[ServiceSelfUpdate] Aggiornato: {rel}", xbmc.LOGINFO)
            except Exception as e:
                xbmc.log(f"[ServiceSelfUpdate] Errore scrittura {rel}: {e}", xbmc.LOGERROR)
    # rimuovi file non più remoti
    sync_orphan_files(remote_paths)

def cleanup_temp_install_folders():
    """
    Rimuove le sorgenti temporanee se gli addon corrispondenti sono installati
    - Utilizza sources_manager per rimuovere le sorgenti da sources.xml
    - Elimina le cartelle fisiche con gli zip
    - Notifica l'utente e richiede riavvio
    """
    cleaned_something = False
    messages = []
    
    # Configurazione per le installazioni temporanee
    temp_installs = [
        {
            "addon_id": "plugin.video.youtube",
            "source_name": "YouTube Install",
            "virtual_path": "special://profile/addon_data/youtube_install/"
        },
        {
            "addon_id": "script.trakt",
            "source_name": "Trakt Install",
            "virtual_path": "special://profile/addon_data/trakt_install/"
        }
    ]
    
    for install in temp_installs:
        # Verifica se l'addon è installato
        if not xbmc.getCondVisibility(f"System.HasAddon({install['addon_id']})"):
            continue
            
        dest_dir = xbmcvfs.translatePath(install['virtual_path'])
        cleaned_this = False

        # 1. Rimuovi da sources.xml usando sources_manager
        # Creiamo un finto repo con le informazioni necessarie
        fake_repo = {
            "name": install['source_name'],
            "url": install['virtual_path']
        }
        
        if sources_manager.remove_source_from_xml(fake_repo):
            cleaned_this = True
            log_msg = f"Rimossa sorgente {install['source_name']} da sources.xml"
            xbmc.log(f"[ServiceSelfUpdate] {log_msg}", xbmc.LOGINFO)
            messages.append(log_msg)
        else:
            log_msg = f"La sorgente {install['source_name']} non trovata in sources.xml"
            xbmc.log(f"[ServiceSelfUpdate] {log_msg}", xbmc.LOGINFO)

        # 2. Rimuovi cartella fisica
        if os.path.exists(dest_dir):
            try:
                shutil.rmtree(dest_dir, ignore_errors=True)
                cleaned_this = True
                log_msg = f"Rimossa cartella {install['source_name']}: {dest_dir}"
                xbmc.log(f"[ServiceSelfUpdate] {log_msg}", xbmc.LOGINFO)
                messages.append(log_msg)
            except Exception as e:
                error_msg = f"Errore rimozione cartella {install['source_name']}: {e}"
                xbmc.log(f"[ServiceSelfUpdate] {error_msg}", xbmc.LOGERROR)
                messages.append(error_msg)
        else:
            log_msg = f"Cartella {install['source_name']} non trovata: {dest_dir}"
            xbmc.log(f"[ServiceSelfUpdate] {log_msg}", xbmc.LOGINFO)

        if cleaned_this:
            cleaned_something = True

    # 3. Notifica e richiedi riavvio
    if cleaned_something:
        xbmc.log("[ServiceSelfUpdate] Pulizia cartelle temporanee completata", xbmc.LOGINFO)
        
        # Crea messaggio di riepilogo
        summary = "Pulizia completata:\n"
        for msg in messages:
            summary += f"- {msg}\n"
        
        xbmcgui.Dialog().notification(
            ADDON_NAME,
            "Rimosse sorgenti temporanee",
            ICON_PATH,
            5000
        )
        
        if xbmcgui.Dialog().yesno(
            ADDON_NAME,
            f"{summary}\nRiavviare Kodi per completare la pulizia?",
            yeslabel="Riavvia ora",
            nolabel="Più tardi"
        ):
            xbmc.executebuiltin("RestartApp")

def check_self_update():
    """
    Controlla se c'è un nuovo commit e, in tal caso, sincronizza tutti i file.
    Notifica solo se ci sono aggiornamenti, mostrando il commit abbreviato e il logo.
    """
    if not github_user or not github_repo:
        xbmc.log("[ServiceSelfUpdate] Parametri GitHub mancanti", xbmc.LOGERROR)
        return
    
    remote_sha = get_remote_commit()
    if not remote_sha:
        return
    
    last_sha = read_last_commit()
    if remote_sha == last_sha:
        xbmc.log("[ServiceSelfUpdate] Nessun aggiornamento disponibile", xbmc.LOGINFO)
        return
    
    xbmc.log(f"[ServiceSelfUpdate] Nuovo commit {remote_sha}", xbmc.LOGINFO)
    
    # sincronizza
    try:
        remote_paths = get_remote_file_list()
        if remote_paths:
            sync_all(remote_paths)
            write_last_commit(remote_sha)
            xbmcgui.Dialog().notification(
                ADDON_NAME,
                f"Addon aggiornato ({remote_sha[:7]})",
                ICON_PATH,
                5000
            )
    except Exception as e:
        xbmc.log(f"[ServiceSelfUpdate] Errore sincronizzazione: {e}", xbmc.LOGERROR)

if __name__ == '__main__':
    check_self_update()
    cleanup_temp_install_folders()