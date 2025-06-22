#!/usr/bin/env python3
# -*- coding: utf-8 -*-

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
ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo('id')
ADDON_NAME = ADDON.getAddonInfo('name')

# Percorsi
PROFILE_PATH = xbmcvfs.translatePath(ADDON.getAddonInfo('profile'))
if not xbmcvfs.exists(PROFILE_PATH):
    xbmcvfs.mkdirs(PROFILE_PATH)
LAST_COMMIT_FILE = os.path.join(PROFILE_PATH, 'last_commit.txt')
ADDON_PATH = xbmcvfs.translatePath(os.path.join('special://home/addons', ADDON_ID))

# Lettura impostazioni GitHub
GITHUB_USER = ADDON.getSetting('github_user')
GITHUB_REPO = ADDON.getSetting('github_repo')
GITHUB_BRANCH = ADDON.getSetting('github_branch') or 'main'


def read_last_commit():
    try:
        if xbmcvfs.exists(LAST_COMMIT_FILE):
            with xbmcvfs.File(LAST_COMMIT_FILE, 'r') as f:
                return f.read().strip()
    except Exception as e:
        xbmc.log(f"[ServiceSelfUpdate] Errore lettura ultimo commit: {e}", xbmc.LOGERROR)
    return ''


def write_last_commit(sha):
    try:
        with xbmcvfs.File(LAST_COMMIT_FILE, 'w') as f:
            f.write(sha)
    except Exception as e:
        xbmc.log(f"[ServiceSelfUpdate] Errore scrittura ultimo commit: {e}", xbmc.LOGERROR)


def get_remote_file_list():
    """
    Restituisce la lista di tutti i file (blob) nel ramo remoto.
    """
    api_tree = f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}/git/trees/{GITHUB_BRANCH}?recursive=1"
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
    Cancella i file locali che non sono più presenti nel repository remoto.
    """
    addon_real = xbmcvfs.translatePath(ADDON_PATH)
    for root, dirs, files in os.walk(addon_real, topdown=False):
        for name in files:
            fullpath = os.path.join(root, name)
            relpath = os.path.relpath(fullpath, addon_real).replace('\\', '/')
            if relpath not in remote_paths:
                try:
                    os.remove(fullpath)
                    xbmc.log(f"[ServiceSelfUpdate] Rimosso orphan: {relpath}", xbmc.LOGINFO)
                except Exception as e:
                    xbmc.log(f"[ServiceSelfUpdate] Errore rimozione orphan {relpath}: {e}", xbmc.LOGERROR)
        # rimuovi directory vuote
        if not os.listdir(root):
            try:
                os.rmdir(root)
            except Exception:
                pass


def update_full(zip_url):
    """
    Scarica l'intero repository come zip e lo estrae sovrascrivendo la cartella addon.
    """
    try:
        resp = urllib.request.urlopen(zip_url, timeout=20)
        data = resp.read()
        zf = zipfile.ZipFile(BytesIO(data))
        addon_real = xbmcvfs.translatePath(ADDON_PATH)
        if os.path.isdir(addon_real):
            shutil.rmtree(addon_real)
        for member in zf.infolist():
            parts = member.filename.split('/', 1)
            if len(parts) < 2:
                continue
            rel = parts[1]
            target = os.path.join(ADDON_PATH, rel)
            if member.is_dir():
                xbmcvfs.mkdirs(xbmcvfs.translatePath(target))
            else:
                dirp = os.path.dirname(target)
                xbmcvfs.mkdirs(xbmcvfs.translatePath(dirp))
                with zf.open(member) as src, xbmcvfs.File(target, 'w') as dst:
                    dst.write(src.read())
        zf.close()
        xbmc.log(f"[ServiceSelfUpdate] Full update completato", xbmc.LOGINFO)
        return True
    except Exception as e:
        xbmc.log(f"[ServiceSelfUpdate] Errore in update_full: {e}", xbmc.LOGERROR)
    return False


def update_incremental(last_sha, remote_sha):
    api_compare = f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}/compare/{last_sha}...{remote_sha}"
    try:
        with urllib.request.urlopen(api_compare, timeout=10) as resp:
            if resp.getcode() != 200:
                xbmc.log(f"[ServiceSelfUpdate] Compare API code: {resp.getcode()}", xbmc.LOGERROR)
                return False
            data = json.loads(resp.read().decode('utf-8'))
            for file_info in data.get('files', []):
                path, status = file_info['filename'], file_info['status']
                local = os.path.join(ADDON_PATH, path)
                real = xbmcvfs.translatePath(local)
                if status == 'removed' and os.path.exists(real):
                    os.remove(real)
                    xbmc.log(f"[ServiceSelfUpdate] Rimosso: {path}", xbmc.LOGINFO)
                elif status in ('added', 'modified'):
                    url = f"https://raw.githubusercontent.com/{GITHUB_USER}/{GITHUB_REPO}/{GITHUB_BRANCH}/{path}"
                    try:
                        with urllib.request.urlopen(url, timeout=20) as r:
                            content = r.read()
                            dp = os.path.dirname(local)
                            xbmcvfs.mkdirs(xbmcvfs.translatePath(dp))
                            with xbmcvfs.File(local, 'w') as f:
                                f.write(content)
                        xbmc.log(f"[ServiceSelfUpdate] Scaricato: {path}", xbmc.LOGINFO)
                    except Exception as e:
                        xbmc.log(f"[ServiceSelfUpdate] Errore download {path}: {e}", xbmc.LOGERROR)
        return True
    except Exception as e:
        xbmc.log(f"[ServiceSelfUpdate] Eccezione confronto: {e}", xbmc.LOGERROR)
    return False


def check_self_update():
    if not GITHUB_USER or not GITHUB_REPO:
        xbmc.log("[ServiceSelfUpdate] Parametri GitHub mancanti", xbmc.LOGERROR)
        return
    api_url = f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}/commits/{GITHUB_BRANCH}"
    try:
        with urllib.request.urlopen(api_url, timeout=10) as resp:
            if resp.getcode() != 200:
                xbmc.log(f"[ServiceSelfUpdate] API response code: {resp.getcode()}", xbmc.LOGERROR)
                return
            data = json.loads(resp.read().decode('utf-8'))
            remote_sha = data.get('sha', '')
            last_sha = read_last_commit()
            if remote_sha and remote_sha != last_sha:
                xbmc.log(f"[ServiceSelfUpdate] Nuovo commit {remote_sha}", xbmc.LOGINFO)
                zip_url = f"https://github.com/{GITHUB_USER}/{GITHUB_REPO}/archive/{GITHUB_BRANCH}.zip"
                if last_sha:
                    success = update_incremental(last_sha, remote_sha)
                else:
                    success = update_full(zip_url)
                if success:
                    # Sincronizza tutti i file: rimuovi orphan e scarica eventuali mancanti
                    remote_files = get_remote_file_list()
                    sync_orphan_files(remote_files)
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
