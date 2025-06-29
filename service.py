# -*- coding: utf-8 -*-
"""
Service Self-Update per Kodi addon: scarica aggiornamenti da GitHub
- Supporta aggiornamento completo e incrementale
- Recupera file mancanti e rimuove orfani
"""

import xbmc
import xbmcaddon
import xbmcvfs
import urllib.request
import json
import os
import xbmcgui
import shutil
import zipfile
from io import BytesIO

# Impostazioni addon
ADDON      = xbmcaddon.Addon()
ADDON_ID   = ADDON.getAddonInfo('id')
ADDON_NAME = ADDON.getAddonInfo('name')

# Percorsi
PROFILE_PATH      = xbmcvfs.translatePath(ADDON.getAddonInfo('profile'))
if not os.path.exists(PROFILE_PATH):
    os.makedirs(PROFILE_PATH, exist_ok=True)
LAST_COMMIT_FILE  = os.path.join(PROFILE_PATH, 'last_commit.txt')
ADDON_PATH        = xbmcvfs.translatePath(os.path.join('special://home/addons', ADDON_ID))

# File da preservare anche se non presenti su GitHub
IGNORE_FILES = {'.firstrun'}

# Lettura impostazioni GitHub
github_user   = ADDON.getSetting('github_user')
github_repo   = ADDON.getSetting('github_repo')
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
    Cancella i file locali che non sono più presenti nel repository remoto,
    eccetto quelli in IGNORE_FILES.
    """
    addon_real = ADDON_PATH
    for root, dirs, files in os.walk(addon_real, topdown=False):
        for name in files:
            fullpath = os.path.join(root, name)
            relpath  = os.path.relpath(fullpath, addon_real).replace('\\', '/')
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


def download_missing(remote_paths):
    """
    Scarica i file remoti non presenti localmente.
    """
    base_url   = f"https://raw.githubusercontent.com/{github_user}/{github_repo}/{github_branch}"
    addon_real = ADDON_PATH
    for rel in remote_paths:
        local_phys = os.path.join(addon_real, rel)
        if not os.path.exists(local_phys):
            url = f"{base_url}/{rel}"
            try:
                with urllib.request.urlopen(url, timeout=20) as r:
                    content = r.read()
                os.makedirs(os.path.dirname(local_phys), exist_ok=True)
                with open(local_phys, 'wb') as f:
                    f.write(content)
                xbmc.log(f"[ServiceSelfUpdate] Scaricato missing: {rel}", xbmc.LOGINFO)
            except Exception as e:
                xbmc.log(f"[ServiceSelfUpdate] Errore download missing {rel}: {e}", xbmc.LOGERROR)


def update_full(zip_url):
    """
    Scarica l'intero repository come zip e lo estrae sovrascrivendo la cartella addon.
    """
    try:
        resp        = urllib.request.urlopen(zip_url, timeout=20)
        zf          = zipfile.ZipFile(BytesIO(resp.read()))
        addon_real  = ADDON_PATH
        if os.path.isdir(addon_real):
            shutil.rmtree(addon_real)
        for member in zf.infolist():
            parts = member.filename.split('/', 1)
            if len(parts) < 2:
                continue
            rel    = parts[1]
            target = os.path.join(addon_real, rel)
            if member.is_dir():
                os.makedirs(target, exist_ok=True)
            else:
                os.makedirs(os.path.dirname(target), exist_ok=True)
                with zf.open(member) as src, open(target, 'wb') as dst:
                    dst.write(src.read())
        xbmc.log("[ServiceSelfUpdate] Full update completato", xbmc.LOGINFO)
        return True
    except Exception as e:
        xbmc.log(f"[ServiceSelfUpdate] Errore in update_full: {e}", xbmc.LOGERROR)
    return False


def update_incremental(last_sha, remote_sha):
    """
    Scarica solo i file aggiunti o modificati rispetto all'ultimo commit.
    """
    api_compare = f"https://api.github.com/repos/{github_user}/{github_repo}/compare/{last_sha}...{remote_sha}"
    try:
        with urllib.request.urlopen(api_compare, timeout=10) as resp:
            if resp.getcode() != 200:
                xbmc.log(f"[ServiceSelfUpdate] Compare API code: {resp.getcode()}", xbmc.LOGERROR)
                return False
            data = json.loads(resp.read().decode('utf-8'))
            for file_info in data.get('files', []):
                path   = file_info['filename']
                status = file_info['status']
                local  = os.path.join(ADDON_PATH, path)
                phys   = xbmcvfs.translatePath(local)
                if status == 'removed' and os.path.exists(phys):
                    os.remove(phys)
                    xbmc.log(f"[ServiceSelfUpdate] Rimosso: {path}", xbmc.LOGINFO)
                elif status in ('added', 'modified'):
                    url = f"https://raw.githubusercontent.com/{github_user}/{github_repo}/{github_branch}/{path}"
                    try:
                        with urllib.request.urlopen(url, timeout=20) as r:
                            content = r.read()
                        os.makedirs(os.path.dirname(phys), exist_ok=True)
                        with open(phys, 'wb') as f:
                            f.write(content)
                        xbmc.log(f"[ServiceSelfUpdate] Scaricato: {path}", xbmc.LOGINFO)
                    except Exception as e:
                        xbmc.log(f"[ServiceSelfUpdate] Errore download {path}: {e}", xbmc.LOGERROR)
        return True
    except Exception as e:
        xbmc.log(f"[ServiceSelfUpdate] Eccezione confronto: {e}", xbmc.LOGERROR)
    return False


def check_self_update():
    """
    Controlla se c'è un nuovo commit e avvia l'aggiornamento.
    """
    if not github_user or not github_repo:
        xbmc.log("[ServiceSelfUpdate] Parametri GitHub mancanti", xbmc.LOGERROR)
        return
    api_url = f"https://api.github.com/repos/{github_user}/{github_repo}/commits/{github_branch}"
    try:
        with urllib.request.urlopen(api_url, timeout=10) as resp:
            if resp.getcode() != 200:
                xbmc.log(f"[ServiceSelfUpdate] API response code: {resp.getcode()}", xbmc.LOGERROR)
                return
            data       = json.loads(resp.read().decode('utf-8'))
            remote_sha = data.get('sha', '')
            last_sha   = read_last_commit()
            if remote_sha and remote_sha != last_sha:
                xbmc.log(f"[ServiceSelfUpdate] Nuovo commit {remote_sha}", xbmc.LOGINFO)
                zip_url = f"https://github.com/{github_user}/{github_repo}/archive/{github_branch}.zip"
                if last_sha:
                    success = update_incremental(last_sha, remote_sha)
                    if success:
                        # scarica eventuali file mancanti
                        download_missing(get_remote_file_list())
                else:
                    success = update_full(zip_url)
                if success:
                    # sincronizza orphan e salva commit
                    sync_orphan_files(get_remote_file_list())
                    write_last_commit(remote_sha)
                    xbmcgui.Dialog().notification(
                        ADDON_NAME,
                        f"Addon aggiornato ({remote_sha[:7]})",
                        xbmcgui.NOTIFICATION_INFO,
                        5000
                    )
            else:
                xbmc.log("[ServiceSelfUpdate] Commit già aggiornato, nessuna azione", xbmc.LOGINFO)
    except Exception as e:
        xbmc.log(f"[ServiceSelfUpdate] Eccezione controllo aggiornamento: {e}", xbmc.LOGERROR)


if __name__ == '__main__':
    check_self_update()
