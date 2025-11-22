# resources/lib/iagl_repo_installer.py
# -*- coding: utf-8 -*-
"""Installer per il repository Zach Morris (IAGL)"""

import xbmc
import xbmcgui
from resources.lib.utils import download_and_extract_zip, log

IAGL_REPO_ZIP_URL = "https://github.com/zach-morris/repository.zachmorris/raw/master/repository.zachmorris/repository.zachmorris-1.0.4.zip"
ADDON_NAME = "IAGL Repository"

def download_iagl_repo():
    """Scarica e installa il repository Zach Morris (IAGL)"""
    try:
        log(f"[{ADDON_NAME}] Inizio download repository IAGL...", xbmc.LOGINFO)
        
        # Mostra notifica di inizio download
        xbmcgui.Dialog().notification(
            ADDON_NAME,
            "Download repository in corso...",
            xbmcgui.NOTIFICATION_INFO,
            3000
        )
        
        # Scarica ed estrai il repository
        result = download_and_extract_zip(IAGL_REPO_ZIP_URL, ADDON_NAME)
        
        if result:
            log(f"[{ADDON_NAME}] Repository installato con successo", xbmc.LOGINFO)
            xbmcgui.Dialog().notification(
                ADDON_NAME,
                "Repository installato con successo!",
                xbmcgui.NOTIFICATION_INFO,
                3000
            )
        else:
            log(f"[{ADDON_NAME}] Errore durante l'installazione", xbmc.LOGERROR)
            xbmcgui.Dialog().notification(
                ADDON_NAME,
                "Errore durante l'installazione",
                xbmcgui.NOTIFICATION_ERROR,
                3000
            )
        
        return result
        
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
