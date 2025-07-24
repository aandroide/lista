# -*- coding: utf-8 -*-
import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs
import os
import shutil
import time
import zipfile
import xml.etree.ElementTree as ET
from resources.lib.utils import log

ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo('id')
ADDON_NAME = ADDON.getAddonInfo('name')
ADDON_ICON = ADDON.getAddonInfo('icon')
ADDON_PATH = ADDON.getAddonInfo('path')

def get_installed_addon_version(addon_id):
    """Recupera la versione di un addon installato leggendo addon.xml"""
    try:
        # Costruisci il percorso alla cartella dell'addon
        addon_path = os.path.join(xbmcvfs.translatePath("special://home/addons"), addon_id)
        
        # Verifica se l'addon è installato
        if not os.path.exists(addon_path):
            return None
            
        # Leggi il file addon.xml
        addon_xml_path = os.path.join(addon_path, "addon.xml")
        if not os.path.exists(addon_xml_path):
            return None
            
        tree = ET.parse(addon_xml_path)
        root = tree.getroot()
        return root.attrib.get('version')
    except Exception as e:
        log(f"Errore lettura versione {addon_id}: {str(e)}", xbmc.LOGERROR)
    return None

def extract_zip_version(zip_path):
    """Estrae la versione da un file ZIP"""
    try:
        with zipfile.ZipFile(zip_path, 'r') as z:
            # Cerca il file addon.xml nello ZIP
            for file_info in z.infolist():
                if file_info.filename.endswith('addon.xml'):
                    with z.open(file_info) as f:
                        tree = ET.parse(f)
                        root = tree.getroot()
                        return root.attrib.get('version')
    except Exception as e:
        log(f"Errore estrazione versione ZIP {zip_path}: {str(e)}", xbmc.LOGERROR)
    return None

def compare_versions(v1, v2):
    """Confronta due stringhe di versione (es. '1.2.3' e '1.2.4')"""
    # Divide le stringhe in componenti numeriche
    v1_parts = [int(p) for p in v1.split('.') if p.isdigit()]
    v2_parts = [int(p) for p in v2.split('.') if p.isdigit()]
    
    # Confronta parte per parte
    for i in range(max(len(v1_parts), len(v2_parts))):
        v1_val = v1_parts[i] if i < len(v1_parts) else 0
        v2_val = v2_parts[i] if i < len(v2_parts) else 0
        
        if v1_val > v2_val:
            return 1
        elif v1_val < v2_val:
            return -1
    
    return 0  # Versioni uguali

def check_for_updates():
    """Controlla se sono disponibili aggiornamenti per YouTube o Trakt"""
    updates = []
    
    # Cartelle di installazione
    youtube_install_dir = os.path.join(ADDON_PATH, "resources", "YouTube Install")
    trakt_install_dir = os.path.join(ADDON_PATH, "resources", "Trakt Install")
    
    # Controllo YouTube
    youtube_installed = get_installed_addon_version("plugin.video.youtube")
    if youtube_installed and os.path.exists(youtube_install_dir):
        for file in os.listdir(youtube_install_dir):
            if file.endswith(".zip"):
                zip_path = os.path.join(youtube_install_dir, file)
                zip_version = extract_zip_version(zip_path)
                if zip_version and compare_versions(zip_version, youtube_installed) > 0:
                    updates.append(("YouTube", zip_version, file))
    
    # Controllo Trakt
    trakt_installed = get_installed_addon_version("script.trakt")
    if trakt_installed and os.path.exists(trakt_install_dir):
        for file in os.listdir(trakt_install_dir):
            if file.endswith(".zip"):
                zip_path = os.path.join(trakt_install_dir, file)
                zip_version = extract_zip_version(zip_path)
                if zip_version and compare_versions(zip_version, trakt_installed) > 0:
                    updates.append(("Trakt", zip_version, file))
    
    return updates

def cleanup_old_install_zips():
    """Pulizia intelligente dei file ZIP di installazione"""
    youtube_install_dir = os.path.join(ADDON_PATH, "resources", "YouTube Install")
    trakt_install_dir = os.path.join(ADDON_PATH, "resources", "Trakt Install")

    # Funzione per verificare se un file ZIP dovrebbe essere eliminato
    def should_delete_zip(zip_path, addon_id):
        # Ottieni versione installata
        installed_version = get_installed_addon_version(addon_id)
        if not installed_version:
            return False  # Addon non installato, mantieni il file
            
        # Estrai versione dallo ZIP
        zip_version = extract_zip_version(zip_path)
        if not zip_version:
            return False  # Non possiamo determinare la versione, mantieni
            
        # Confronta le versioni
        return installed_version == zip_version

    # Processa YouTube
    if os.path.exists(youtube_install_dir):
        for file in os.listdir(youtube_install_dir):
            if file.endswith(".zip"):
                zip_path = os.path.join(youtube_install_dir, file)
                if should_delete_zip(zip_path, "plugin.video.youtube"):
                    try:
                        os.remove(zip_path)
                        log(f"Rimosso file YouTube: {file} (versione corrispondente)")
                    except Exception as e:
                        log(f"Errore rimozione YouTube: {str(e)}", xbmc.LOGERROR)

    # Processa Trakt
    if os.path.exists(trakt_install_dir):
        for file in os.listdir(trakt_install_dir):
            if file.endswith(".zip"):
                zip_path = os.path.join(trakt_install_dir, file)
                if should_delete_zip(zip_path, "script.trakt"):
                    try:
                        os.remove(zip_path)
                        log(f"Rimosso file Trakt: {file} (versione corrispondente)")
                    except Exception as e:
                        log(f"Errore rimozione Trakt: {str(e)}", xbmc.LOGERROR)

def show_update_notification(updates):
    """Mostra una notifica se ci sono aggiornamenti disponibili"""
    if not updates:
        return
    
    message = "Aggiornamenti disponibili:\n\n"
    for update in updates:
        name, version, filename = update
        message += f"[COLOR lime]{name}[/COLOR] v{version}\n"
        message += f"File: [COLOR yellow]{filename}[/COLOR]\n\n"
    
    message += "Vai su:\n[COLOR lime]Add-on → Installa da file zip[/COLOR]\n"
    message += "per installare la nuova versione"
    
    # Notifica con timeout lungo (15 secondi)
    xbmcgui.Dialog().notification(
        ADDON_NAME,
        "Aggiornamenti disponibili!",
        ADDON_ICON,
        15000
    )
    
    # Mostra anche un dialog con informazioni dettagliate
    xbmcgui.Dialog().ok(ADDON_NAME, message)

if __name__ == "__main__":
    monitor = xbmc.Monitor()
    log("Service avviato")

    # Esegui un primo controllo all'avvio
    cleanup_old_install_zips()
    
    # Controlla aggiornamenti disponibili
    updates = check_for_updates()
    if updates:
        show_update_notification(updates)

    while not monitor.abortRequested():
        if monitor.waitForAbort(3600):  # Controlla ogni ora
            break
        
        cleanup_old_install_zips()
        
        # Controlla aggiornamenti ogni 6 ore
        if time.localtime().tm_hour % 6 == 0:
            updates = check_for_updates()
            if updates:
                show_update_notification(updates)

    log("Service terminato")
