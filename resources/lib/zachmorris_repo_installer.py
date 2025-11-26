# -*- coding: utf-8 -*-
# resources/lib/zachmorris_repo_installer.py
import xbmc
import xbmcgui
import xbmcvfs
import urllib.request
import json
import zipfile
import os

def download_zachmorris_repo():
    """Scarica e installa il repository Zach Morris direttamente dalla release GitHub"""
    addon_name = "Zach Morris Repo"
    
    try:
        # URL API dell'ultima release
        api_url = "https://api.github.com/repos/zach-morris/repository.zachmorris/releases/latest"
        
        # Ottieni informazioni sulla release
        with urllib.request.urlopen(api_url) as response:
            release_data = json.loads(response.read().decode('utf-8'))
        
        # Trova l'asset ZIP del repository
        zip_asset = None
        for asset in release_data.get('assets', []):
            asset_name = asset.get('name', '')
            if asset_name.lower().startswith('repository.zachmorris') and asset_name.lower().endswith('.zip'):
                zip_asset = asset
                break
        
        if not zip_asset:
            raise Exception("Nessun file repository trovato nella release")
        
        zip_url = zip_asset['browser_download_url']
        
        # Usa la funzione di utilità per scaricare ed estrarre
        from resources.lib.utils import download_and_extract_zip
        success = download_and_extract_zip(zip_url, addon_name)
        
        if success:
            xbmcgui.Dialog().notification(
                addon_name,
                "Repository installato con successo",
                xbmcgui.NOTIFICATION_INFO,
                3000
            )
        return success
        
    except Exception as e:
        xbmc.log(f"[{addon_name}] Errore: {str(e)}", xbmc.LOGERROR)
        xbmcgui.Dialog().notification(
            addon_name,
            f"Errore installazione: {str(e)}",
            xbmcgui.NOTIFICATION_ERROR,
            5000
        )
        return False
