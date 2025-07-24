# -*- coding: utf-8 -*-
import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs
import os
import time
import zipfile
import xml.etree.ElementTree as ET
import re
import traceback
from resources.lib.utils import log

ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo('id')
ADDON_NAME = ADDON.getAddonInfo('name')
ADDON_ICON = ADDON.getAddonInfo('icon')

def get_installed_addon_version(addon_id):
    """Recupera la versione di un addon installato leggendo addon.xml"""
    try:
        # Utilizza percorso universale per la cartella addons
        addon_path = xbmcvfs.translatePath(f"special://home/addons/{addon_id}")
        
        if not xbmcvfs.exists(addon_path):
            log(f"Addon {addon_id} non installato", xbmc.LOGINFO)
            return None
            
        addon_xml_path = os.path.join(addon_path, "addon.xml")
        if not xbmcvfs.exists(addon_xml_path):
            log(f"File addon.xml non trovato per {addon_id}", xbmc.LOGINFO)
            return None
            
        # Leggi il contenuto del file con xbmcvfs
        file = xbmcvfs.File(addon_xml_path)
        content = file.read()
        file.close()
        
        match = re.search(r'version="([^"]+)"', content)
        if match:
            version = match.group(1)
            log(f"Versione installata {addon_id}: {version}", xbmc.LOGINFO)
            return version
    except Exception as e:
        log(f"ERRORE lettura versione {addon_id}: {traceback.format_exc()}", xbmc.LOGERROR)
    return None

def extract_zip_version(zip_path):
    """Estrae la versione da un file ZIP"""
    try:
        with zipfile.ZipFile(zip_path, 'r') as z:
            # Cerca il file addon.xml nello ZIP
            for file_info in z.infolist():
                if file_info.filename.endswith('addon.xml'):
                    with z.open(file_info) as f:
                        content = f.read().decode('utf-8')
                        # Estrai la versione usando regex
                        match = re.search(r'version="([^"]+)"', content)
                        if match:
                            version = match.group(1)
                            log(f"Versione ZIP {os.path.basename(zip_path)}: {version}", xbmc.LOGINFO)
                            return version
        log(f"File addon.xml non trovato in {zip_path}", xbmc.LOGINFO)
    except Exception as e:
        log(f"ERRORE estrazione versione ZIP {zip_path}: {traceback.format_exc()}", xbmc.LOGERROR)
    return None

def compare_versions(v1, v2):
    """Confronta due versioni, supporta numeri e suffissi"""
    if not v1 or not v2:
        return 0
        
    # Normalizza le versioni
    v1 = v1.replace('-', '.').lower()
    v2 = v2.replace('-', '.').lower()
    
    # Estrai parti numeriche principali
    v1_main = re.sub(r'[^0-9.]', '', v1)
    v2_main = re.sub(r'[^0-9.]', '', v2)
    
    # Confronta parti numeriche
    v1_parts = [int(p) for p in v1_main.split('.') if p.isdigit()]
    v2_parts = [int(p) for p in v2_main.split('.') if p.isdigit()]
    
    for i in range(max(len(v1_parts), len(v2_parts))):
        v1_val = v1_parts[i] if i < len(v1_parts) else 0
        v2_val = v2_parts[i] if i < len(v2_parts) else 0
        
        if v1_val > v2_val:
            return 1
        elif v1_val < v2_val:
            return -1
    
    # Se le parti numeriche sono uguali, considera i suffissi
    if "beta" in v2 and "beta" not in v1:
        return -1  # v2 è una beta mentre v1 è stabile → considera nuova versione
    
    return 0

def check_for_updates():
    """Controlla aggiornamenti disponibili per YouTube e Trakt"""
    updates = []
    
    try:
        # Percorsi universali per le cartelle di installazione
        youtube_install_dir = xbmcvfs.translatePath("special://profile/addon_data/plugin.video.youtube/youtube_install/")
        trakt_install_dir = xbmcvfs.translatePath("special://profile/addon_data/plugin.video.youtube/trakt_install/")
        
        # Controllo YouTube
        installed_yt = get_installed_addon_version("plugin.video.youtube")
        if installed_yt and xbmcvfs.exists(youtube_install_dir):
            log(f"Controllo aggiornamenti YouTube in {youtube_install_dir}", xbmc.LOGINFO)
            dirs, files = xbmcvfs.listdir(youtube_install_dir)
            for file in files:
                if file.lower().endswith(".zip"):
                    zip_path = os.path.join(youtube_install_dir, file)
                    if xbmcvfs.exists(zip_path):
                        zip_version = extract_zip_version(zip_path)
                        if zip_version:
                            comparison = compare_versions(installed_yt, zip_version)
                            if comparison < 0:
                                log(f"AGGIORNAMENTO DISPONIBILE: YouTube {installed_yt} → {zip_version}", xbmc.LOGINFO)
                                updates.append(("YouTube", installed_yt, zip_version, file))
        
        # Controllo Trakt
        installed_trakt = get_installed_addon_version("script.trakt")
        if installed_trakt and xbmcvfs.exists(trakt_install_dir):
            log(f"Controllo aggiornamenti Trakt in {trakt_install_dir}", xbmc.LOGINFO)
            dirs, files = xbmcvfs.listdir(trakt_install_dir)
            for file in files:
                if file.lower().endswith(".zip"):
                    zip_path = os.path.join(trakt_install_dir, file)
                    if xbmcvfs.exists(zip_path):
                        zip_version = extract_zip_version(zip_path)
                        if zip_version:
                            comparison = compare_versions(installed_trakt, zip_version)
                            if comparison < 0:
                                log(f"AGGIORNAMENTO DISPONIBILE: Trakt {installed_trakt} → {zip_version}", xbmc.LOGINFO)
                                updates.append(("Trakt", installed_trakt, zip_version, file))
    except Exception as e:
        log(f"ERRORE durante check_for_updates: {traceback.format_exc()}", xbmc.LOGERROR)
    
    return updates

def cleanup_old_install_zips():
    """Pulizia intelligente dei file ZIP di installazione"""
    try:
        # Percorsi universali
        youtube_install_dir = xbmcvfs.translatePath("special://profile/addon_data/plugin.video.youtube/youtube_install/")
        trakt_install_dir = xbmcvfs.translatePath("special://profile/addon_data/plugin.video.youtube/trakt_install/")
        
        # YouTube
        if xbmcvfs.exists(youtube_install_dir):
            dirs, files = xbmcvfs.listdir(youtube_install_dir)
            for file in files:
                if file.lower().endswith(".zip"):
                    zip_path = os.path.join(youtube_install_dir, file)
                    if xbmcvfs.exists(zip_path):
                        installed_version = get_installed_addon_version("plugin.video.youtube")
                        zip_version = extract_zip_version(zip_path)
                        
                        if installed_version and zip_version and installed_version == zip_version:
                            try:
                                xbmcvfs.delete(zip_path)
                                log(f"Rimosso file YouTube: {file} (versione corrispondente)", xbmc.LOGINFO)
                            except Exception as e:
                                log(f"Errore rimozione YouTube: {traceback.format_exc()}", xbmc.LOGERROR)
        
        # Trakt
        if xbmcvfs.exists(trakt_install_dir):
            dirs, files = xbmcvfs.listdir(trakt_install_dir)
            for file in files:
                if file.lower().endswith(".zip"):
                    zip_path = os.path.join(trakt_install_dir, file)
                    if xbmcvfs.exists(zip_path):
                        installed_version = get_installed_addon_version("script.trakt")
                        zip_version = extract_zip_version(zip_path)
                        
                        if installed_version and zip_version and installed_version == zip_version:
                            try:
                                xbmcvfs.delete(zip_path)
                                log(f"Rimosso file Trakt: {file} (versione corrispondente)", xbmc.LOGINFO)
                            except Exception as e:
                                log(f"Errore rimozione Trakt: {traceback.format_exc()}", xbmc.LOGERROR)
    except Exception as e:
        log(f"ERRORE durante cleanup_old_install_zips: {traceback.format_exc()}", xbmc.LOGERROR)

def show_update_notification(updates):
    """Mostra una notifica se ci sono aggiornamenti disponibili"""
    if not updates:
        return
    
    try:
        message = "Sono disponibili aggiornamenti:\n\n"
        for update in updates:
            name, old_ver, new_ver, filename = update
            message += f"[COLOR lime]{name}[/COLOR]:\n"
            message += f"• Versione attuale: [COLOR red]{old_ver}[/COLOR]\n"
            message += f"• Nuova versione: [COLOR yellow]{new_ver}[/COLOR]\n"
            message += f"• File: [COLOR cyan]{filename}[/COLOR]\n\n"
        
        message += "Per installare:\n"
        message += "1. Vai su: [COLOR lime]Add-on → Installa da file zip[/COLOR]\n"
        message += "2. Scegli la cartella corrispondente"
        
        # Mostra dialog con informazioni dettagliate
        xbmcgui.Dialog().ok(f"{ADDON_NAME} - Aggiornamenti disponibili", message)
    except Exception as e:
        log(f"ERRORE durante show_update_notification: {traceback.format_exc()}", xbmc.LOGERROR)

if __name__ == "__main__":
    monitor = xbmc.Monitor()
    log(f"{ADDON_NAME} service avviato", xbmc.LOGINFO)
    
    try:
        # Esegui un primo controllo all'avvio
        cleanup_old_install_zips()
        
        # Controlla subito gli aggiornamenti
        updates = check_for_updates()
        if updates:
            log("Trovati aggiornamenti disponibili", xbmc.LOGINFO)
            show_update_notification(updates)
        else:
            log("Nessun aggiornamento disponibile", xbmc.LOGINFO)
        
        # Contatore per controlli periodici
        last_update_check = time.time()
        
        while not monitor.abortRequested():
            if monitor.waitForAbort(10):  # Controlla ogni 10 secondi
                break
            
            # Controlla aggiornamenti ogni 30 minuti
            current_time = time.time()
            if current_time - last_update_check > 1800:  # 30 minuti
                last_update_check = current_time
                
                # Esegui pulizia prima del controllo
                cleanup_old_install_zips()
                
                # Controlla aggiornamenti
                updates = check_for_updates()
                if updates:
                    log("Trovati aggiornamenti disponibili (controllo periodico)", xbmc.LOGINFO)
                    show_update_notification(updates)

    except Exception as e:
        log(f"ERRORE CRITICO nel service: {traceback.format_exc()}", xbmc.LOGERROR)
    
    log(f"{ADDON_NAME} service terminato", xbmc.LOGINFO)
