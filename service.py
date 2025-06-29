# -*- coding: utf-8 -*-
"""
Service Self-Update per Kodi addon: sincronizza tutti i file presenti su GitHub con quelli locali
- Scarica file mancanti o modificati
- Rimuove file locali non più presenti (orfani)
"""

import xbmc
import xbmcaddon
import xbmcvfs
import urllib.request
import json
import os
import xbmcgui
import shutil

# Impostazioni addon
ADDON      = xbmcaddon.Addon()
ADDON_ID   = ADDON.getAddonInfo('id')
ADDON_NAME = ADDON.getAddonInfo('name')

# Percorsi
PROFILE_PATH     = xbmcvfs.translatePath(ADDON.getAddonInfo('profile'))
if not os.path.exists(PROFILE_PATH):
    os.makedirs(PROFILE_PATH, exist_ok=True)
LAST_COMMIT_FILE = os.path.join(PROFILE_PATH, 'last_commit.txt')  # opzionale
ADDON_PATH       = xbmcvfs.translatePath(os.path.join('special://home/addons', ADDON_ID))

# File da preservare anche se non presenti su GitHub
IGNORE_FILES = {'.firstrun'}

# Lettura impostazioni GitHub
github_user   = ADDON.getSetting('github_user')
github_repo   = ADDON.getSetting('github_repo')
github_branch = ADDON.getSetting('github_branch') or 'main'


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
    Rimuove i file locali che non sono più presenti nel repository remoto,
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


def sync_all():
    """
    Sincronizza tutti i file remoti con quelli locali.
    Scarica file mancanti o modificati e rimuove orfani.
    """
    remote_paths = get_remote_file_list()
    if not remote_paths:
        return
    base_url   = f"https://raw.githubusercontent.com/{github_user}/{github_repo}/{github_branch}"
    addon_real = ADDON_PATH
    for rel in remote_paths:
        phys = os.path.join(addon_real, rel)
        url  = f"{base_url}/{rel}"
        try:
            with urllib.request.urlopen(url, timeout=20) as r:
                content = r.read()
        except Exception as e:
            xbmc.log(f"[ServiceSelfUpdate] Errore fetch {rel}: {e}", xbmc.LOGERROR)
            continue
        # determina se scrivere: mancante o modificato
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
                xbmc.log(f"[ServiceSelfUpdate] Aggiornato/Scaricato: {rel}", xbmc.LOGINFO)
            except Exception as e:
                xbmc.log(f"[ServiceSelfUpdate] Errore scrittura {rel}: {e}", xbmc.LOGERROR)
    # rimuove file locali non più remoti
    sync_orphan_files(remote_paths)


def check_self_update():
    """
    Avvia sincronizzazione completa all'avvio.
    """
    if not github_user or not github_repo:
        xbmc.log("[ServiceSelfUpdate] Parametri GitHub mancanti", xbmc.LOGERROR)
        return
    xbmc.log("[ServiceSelfUpdate] Avvio sincronizzazione completa", xbmc.LOGINFO)
    try:
        sync_all()
        xbmcgui.Dialog().notification(
            ADDON_NAME,
            "Addon sincronizzato",
            xbmcgui.NOTIFICATION_INFO,
            5000
        )
    except Exception as e:
        xbmc.log(f"[ServiceSelfUpdate] Errore sincronizzazione: {e}", xbmc.LOGERROR)


if __name__ == '__main__':
    check_self_update()
