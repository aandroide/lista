# resources/lib/iagl_repo_installer.py
# -*- coding: utf-8 -*-
"""Installer per il repository Zach Morris (IAGL)"""

import os
import shutil
import zipfile
import xbmc
import xbmcgui
import xbmcaddon
import xbmcvfs
from resources.lib.utils import log, set_addon_enabled

ADDON = xbmcaddon.Addon()
ADDON_PATH = xbmcvfs.translatePath(ADDON.getAddonInfo('path'))
ADDON_NAME = "IAGL Repository"
REPO_ID = "repository.zachmorris"

def download_iagl_repo():
    """Installa il repository Zach Morris (IAGL) estraendo il ZIP locale"""
    try:
        log(f"[{ADDON_NAME}] Inizio installazione repository IAGL...", xbmc.LOGINFO)
        
        # Percorso del repository nella cartella locale
        repo_source = os.path.join(ADDON_PATH, 'resources', 'repositories', 'repository.zachmorris')
        
        # Verifica che la sorgente esista
        if not os.path.exists(repo_source):
            error_msg = "Repository non trovato nella cartella locale"
            log(f"[{ADDON_NAME}] {error_msg}: {repo_source}", xbmc.LOGERROR)
            xbmcgui.Dialog().notification(
                ADDON_NAME,
                error_msg,
                xbmcgui.NOTIFICATION_ERROR,
                5000
            )
            return False
        
        # Crea un file ZIP temporaneo del repository
        packages_dir = xbmcvfs.translatePath("special://home/addons/packages/")
        if not os.path.exists(packages_dir):
            os.makedirs(packages_dir)
        
        zip_path = os.path.join(packages_dir, f"{REPO_ID}-1.0.4.zip")
        
        # Mostra notifica di inizio installazione
        xbmcgui.Dialog().notification(
            ADDON_NAME,
            "Installazione repository in corso...",
            xbmcgui.NOTIFICATION_INFO,
            3000
        )
        
        # Crea il file ZIP dal repository locale
        log(f"[{ADDON_NAME}] Creazione ZIP temporaneo: {zip_path}", xbmc.LOGINFO)
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(repo_source):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.join(REPO_ID, os.path.relpath(file_path, repo_source))
                    zipf.write(file_path, arcname)
        
        # Estrai il ZIP nella cartella addons
        extract_to = xbmcvfs.translatePath("special://home/addons/")
        log(f"[{ADDON_NAME}] Estrazione ZIP in: {extract_to}", xbmc.LOGINFO)
        
        with zipfile.ZipFile(zip_path, 'r') as z:
            z.extractall(extract_to)
        
        # Aggiorna gli addon e abilita il repository
        xbmc.executebuiltin('UpdateLocalAddons')
        xbmc.sleep(500)
        
        if xbmc.getCondVisibility(f"System.HasAddon({REPO_ID})"):
            set_addon_enabled(REPO_ID)
            xbmc.executebuiltin('UpdateLocalAddons')
            log(f"[{ADDON_NAME}] Repository abilitato", xbmc.LOGINFO)
        
        # Rimuovi il file ZIP temporaneo
        try:
            os.remove(zip_path)
            log(f"[{ADDON_NAME}] Rimosso ZIP temporaneo", xbmc.LOGINFO)
        except:
            pass
        
        log(f"[{ADDON_NAME}] Repository installato con successo", xbmc.LOGINFO)
        xbmcgui.Dialog().notification(
            ADDON_NAME,
            "Repository installato con successo!",
            xbmcgui.NOTIFICATION_INFO,
            3000
        )
        
        return True
        
    except Exception as e:
        error_msg = f"Errore: {str(e)}"
        log(f"[{ADDON_NAME}] {error_msg}", xbmc.LOGERROR)
        xbmcgui.Dialog().notification(
            ADDON_NAME,
            error_msg,
            xbmcgui.NOTIFICATION_ERROR,
            5000
        )
        return False
