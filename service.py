#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import xbmc
import xbmcaddon
import xbmcvfs
import urllib.request
import json
import os
import xbmcgui
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
            f = xbmcvfs.File(LAST_COMMIT_FILE, 'r')
            sha = f.read().strip()
            f.close()
            return sha
    except Exception as e:
        xbmc.log(f"[ServiceSelfUpdate] Errore lettura ultimo commit: {e}", xbmc.LOGERROR)
    return ''


def write_last_commit(sha):
    try:
        f = xbmcvfs.File(LAST_COMMIT_FILE, 'w')
        f.write(sha)
        f.close()
    except Exception as e:
        xbmc.log(f"[ServiceSelfUpdate] Errore scrittura ultimo commit: {e}", xbmc.LOGERROR)


def update_from_zip(zip_url):
    """
    Scarica lo zip dal repository e lo estrae direttamente nella cartella dell'addon,
    sovrascrivendo i file esistenti e mantenendo la struttura interna senza la cartella radice.
    """
    try:
        # Scarica in memoria
        resp = urllib.request.urlopen(zip_url, timeout=20)
        data = resp.read()
        zf = zipfile.ZipFile(BytesIO(data))
        for member in zf.infolist():
            # Salta la cartella radice del zip
            parts = member.filename.split('/', 1)
            if len(parts) < 2:
                continue
            relpath = parts[1]
            target_path = os.path.join(ADDON_PATH, relpath)

            if member.is_dir():
                xbmcvfs.mkdirs(xbmcvfs.translatePath(target_path))
            else:
                # Crea cartella se non esiste
                dirpath = os.path.dirname(target_path)
                if not xbmcvfs.exists(xbmcvfs.translatePath(dirpath)):
                    xbmcvfs.mkdirs(xbmcvfs.translatePath(dirpath))
                # Estrai file
                with zf.open(member) as src:
                    data_file = src.read()
                    f = xbmcvfs.File(target_path, 'w')
                    f.write(data_file)
                    f.close()
        zf.close()
        xbmc.log(f"[ServiceSelfUpdate] Estrazione ZIP completata in {ADDON_PATH}", xbmc.LOGINFO)
    except Exception as e:
        xbmc.log(f"[ServiceSelfUpdate] Errore in update_from_zip: {e}", xbmc.LOGERROR)
        return False
    return True


def check_self_update():
    if not GITHUB_USER or not GITHUB_REPO:
        xbmc.log("[ServiceSelfUpdate] Parametri GitHub mancanti", xbmc.LOGERROR)
        return

    api_url = f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}/commits/{GITHUB_BRANCH}"
    xbmc.log(f"[ServiceSelfUpdate] Controllo commit su {GITHUB_USER}/{GITHUB_REPO}@{GITHUB_BRANCH}", xbmc.LOGINFO)

    try:
        with urllib.request.urlopen(api_url, timeout=10) as resp:
            if resp.getcode() != 200:
                xbmc.log(f"[ServiceSelfUpdate] API response code: {resp.getcode()}", xbmc.LOGERROR)
                return
            data = json.loads(resp.read().decode('utf-8'))
            remote_sha = data.get('sha', '')
            if not remote_sha:
                xbmc.log("[ServiceSelfUpdate] SHA mancante nella risposta API", xbmc.LOGERROR)
                return

            last_sha = read_last_commit()
            if remote_sha != last_sha:
                xbmc.log(f"[ServiceSelfUpdate] Nuovo commit {remote_sha}", xbmc.LOGINFO)
                zip_url = f"https://github.com/{GITHUB_USER}/{GITHUB_REPO}/archive/{GITHUB_BRANCH}.zip"
                if update_from_zip(zip_url):
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
