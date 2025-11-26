# -*- coding: utf-8 -*-
# resources/lib/zachmorris_repo_installer.py
import xbmc
import xbmcgui
import xbmcvfs
import urllib.request
import zipfile
import os
import shutil

def download_zachmorris_repo():
    """Scarica e installa il repository Zach Morris"""
    addon_name = "Zach Morris Repo"
    
    try:
        # URL per scaricare l'intero repository come ZIP
        repo_zip_url = "https://github.com/zach-morris/repository.zachmorris/archive/refs/heads/master.zip"
        
        # Percorsi
        packages_dir = xbmcvfs.translatePath("special://home/addons/packages/")
        addons_dir = xbmcvfs.translatePath("special://home/addons/")
        temp_zip = os.path.join(packages_dir, "zachmorris_temp.zip")
        
        xbmc.log(f"[{addon_name}] Download da: {repo_zip_url}", xbmc.LOGINFO)
        
        # Scarica il repository completo
        urllib.request.urlretrieve(repo_zip_url, temp_zip)
        
        # Estrai il repository
        with zipfile.ZipFile(temp_zip, 'r') as zip_ref:
            # Il repository viene estratto come repository.zachmorris-master/
            zip_ref.extractall(packages_dir)
        
        # Il repository estratto è in repository.zachmorris-master/repository.zachmorris/
        extracted_repo_path = os.path.join(packages_dir, "repository.zachmorris-master", "repository.zachmorris")
        
        if not os.path.exists(extracted_repo_path):
            raise Exception("Struttura repository non trovata dopo estrazione")
        
        # Copia la cartella repository.zachmorris in addons/
        final_repo_path = os.path.join(addons_dir, "repository.zachmorris")
        
        # Rimuovi se esiste già
        if os.path.exists(final_repo_path):
            shutil.rmtree(final_repo_path)
        
        # Copia la directory
        shutil.copytree(extracted_repo_path, final_repo_path)
        
        # Pulizia
        os.remove(temp_zip)
        shutil.rmtree(os.path.join(packages_dir, "repository.zachmorris-master"))
        
        # Aggiorna Kodi
        xbmc.executebuiltin('UpdateLocalAddons')
        xbmc.sleep(500)
        
        # Abilita il repository
        if xbmc.getCondVisibility("System.HasAddon(repository.zachmorris)"):
            req = {
                "jsonrpc": "2.0",
                "method": "Addons.SetAddonEnabled",
                "params": {"addonid": "repository.zachmorris", "enabled": True},
                "id": 1
            }
            import json
            xbmc.executeJSONRPC(json.dumps(req))
            xbmc.executebuiltin('UpdateLocalAddons')
        
        xbmcgui.Dialog().notification(
            addon_name,
            "Installazione completata",
            xbmcgui.NOTIFICATION_INFO,
            3000
        )
        return True
        
    except Exception as e:
        xbmc.log(f"[{addon_name}] Errore: {e}", xbmc.LOGERROR)
        import traceback
        xbmc.log(f"[{addon_name}] Traceback: {traceback.format_exc()}", xbmc.LOGERROR)
        xbmcgui.Dialog().notification(
            addon_name,
            f"Errore: {str(e)}",
            xbmcgui.NOTIFICATION_ERROR,
            5000
        )
        return False
