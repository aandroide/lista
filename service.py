# -*- coding: utf-8 -*-
import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs
import os
import time
import re
import traceback
import json
import urllib.request
from resources.lib.utils import log

ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo('id')
ADDON_NAME = ADDON.getAddonInfo('name')
ADDON_ICON = ADDON.getAddonInfo('icon')

# Percorsi API
YOUTUBE_API_URL = "https://api.github.com/repos/yt-dlp/yt-dlp/releases/latest"
TRAKT_API_URL = "https://api.github.com/repos/trakt/script.trakt/releases/latest"

# Cache delle versioni (per evitare troppe richieste)
version_cache = {}
cache_expiration = 0
CACHE_DURATION = 3600  # 1 ora

def get_installed_addon_version(addon_id):
    """Recupera la versione di un addon installato"""
    try:
        addon = xbmcaddon.Addon(addon_id)
        version = addon.getAddonInfo('version')
        log(f"Versione installata {addon_id}: {version}", xbmc.LOGINFO)
        return version
    except:
        return None

def get_latest_online_version(api_url):
    """Recupera l'ultima versione disponibile online"""
    global version_cache, cache_expiration
    
    # Controlla la cache
    current_time = time.time()
    if api_url in version_cache and current_time < cache_expiration:
        return version_cache[api_url]
    
    try:
        # Crea la richiesta
        req = urllib.request.Request(api_url)
        req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)')
        
        # Esegui la richiesta
        with urllib.request.urlopen(req, timeout=10) as response:
            if response.getcode() != 200:
                return None
                
            data = json.loads(response.read().decode('utf-8'))
            version = data.get('tag_name', '')
            
            # Pulisci la versione (rimuovi 'v' iniziale)
            version = re.sub(r'^v', '', version, flags=re.IGNORECASE)
            
            # Aggiorna la cache
            version_cache[api_url] = version
            cache_expiration = current_time + CACHE_DURATION
            
            log(f"Versione online da {api_url}: {version}", xbmc.LOGINFO)
            return version
            
    except Exception as e:
        log(f"Errore accesso a {api_url}: {str(e)}", xbmc.LOGERROR)
        return None

def compare_versions(v1, v2):
    """Confronta due versioni"""
    if not v1 or not v2:
        return 0
        
    # Normalizza le versioni
    v1 = v1.replace('-', '.').lower()
    v2 = v2.replace('-', '.').lower()
    
    # Estrai parti numeriche
    v1_parts = []
    for part in v1.split('.'):
        if part.isdigit():
            v1_parts.append(int(part))
    
    v2_parts = []
    for part in v2.split('.'):
        if part.isdigit():
            v2_parts.append(int(part))
    
    # Confronta parte per parte
    for i in range(max(len(v1_parts), len(v2_parts))):
        v1_val = v1_parts[i] if i < len(v1_parts) else 0
        v2_val = v2_parts[i] if i < len(v2_parts) else 0
        
        if v1_val > v2_val:
            return 1
        elif v1_val < v2_val:
            return -1
    
    return 0

def check_for_updates():
    """Controlla se sono disponibili aggiornamenti online"""
    updates = []
    
    try:
        # Controllo YouTube
        installed_yt = get_installed_addon_version("plugin.video.youtube")
        if installed_yt:
            online_yt = get_latest_online_version(YOUTUBE_API_URL)
            if online_yt and compare_versions(installed_yt, online_yt) < 0:
                log(f"AGGIORNAMENTO DISPONIBILE: YouTube {installed_yt} → {online_yt}", xbmc.LOGINFO)
                updates.append(("YouTube", installed_yt, online_yt))
        
        # Controllo Trakt
        installed_trakt = get_installed_addon_version("script.trakt")
        if installed_trakt:
            online_trakt = get_latest_online_version(TRAKT_API_URL)
            if online_trakt and compare_versions(installed_trakt, online_trakt) < 0:
                log(f"AGGIORNAMENTO DISPONIBILE: Trakt {installed_trakt} → {online_trakt}", xbmc.LOGINFO)
                updates.append(("Trakt", installed_trakt, online_trakt))
    except Exception as e:
        log(f"ERRORE durante check_for_updates: {traceback.format_exc()}", xbmc.LOGERROR)
    
    return updates

def show_update_notification(updates):
    """Mostra una notifica se ci sono aggiornamenti disponibili"""
    if not updates:
        return
    
    try:
        message = "Sono disponibili aggiornamenti:\n\n"
        for update in updates:
            name, old_ver, new_ver = update
            message += f"[COLOR lime]{name}[/COLOR]:\n"
            message += f"• Versione attuale: [COLOR red]{old_ver}[/COLOR]\n"
            message += f"• Nuova versione: [COLOR yellow]{new_ver}[/COLOR]\n\n"
        
        message += "Per installare gli aggiornamenti:\n"
        message += "1. Apri l'addon [B]Installer[/B]\n"
        message += "2. Vai alla sezione [B]YouTube[/B] o [B]Trakt[/B]\n"
        message += "3. Segui le istruzioni per scaricare la nuova versione"
        
        # Mostra dialog con informazioni dettagliate
        xbmcgui.Dialog().ok(f"{ADDON_NAME} - Aggiornamenti disponibili", message)
    except Exception as e:
        log(f"ERRORE durante show_update_notification: {traceback.format_exc()}", xbmc.LOGERROR)

def main():
    """Funzione principale del service"""
    log(f"{ADDON_NAME} service avviato", xbmc.LOGINFO)
    monitor = xbmc.Monitor()
    
    # Attendi 60 secondi per dare tempo a Kodi di avviarsi completamente
    monitor.waitForAbort(60)
    
    # Controllo iniziale
    updates = check_for_updates()
    if updates:
        log("Trovati aggiornamenti disponibili", xbmc.LOGINFO)
        show_update_notification(updates)
    else:
        log("Nessun aggiornamento disponibile", xbmc.LOGINFO)
    
    # Controlla ogni 6 ore (21600 secondi)
    while not monitor.abortRequested():
        if monitor.waitForAbort(21600):
            break
        
        updates = check_for_updates()
        if updates:
            log("Trovati aggiornamenti (controllo periodico)", xbmc.LOGINFO)
            show_update_notification(updates)

    log(f"{ADDON_NAME} service terminato", xbmc.LOGINFO)

if __name__ == "__main__":
    main()
