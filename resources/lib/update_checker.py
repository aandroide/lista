# -*- coding: utf-8 -*-
import os
import shutil
import urllib.request
import urllib.error
import xbmc
import xbmcgui
import traceback
from .utils import log, safe_download_file

def check_for_updates(ADDON_NAME, ADDON_ICON, LOCAL_JSON, BACKUP_JSON, LAST_ETAG_FILE, REMOTE_URL):
    """
    Controlla gli aggiornamenti disponibili per i repository
    
    Args:
        ADDON_NAME (str): Nome dell'addon
        ADDON_ICON (str): Percorso dell'icona dell'addon
        LOCAL_JSON (str): Percorso del file JSON locale
        BACKUP_JSON (str): Percorso del file JSON di backup
        LAST_ETAG_FILE (str): Percorso del file che contiene l'ultimo ETag
        REMOTE_URL (str): URL del file JSON remoto
        
    Returns:
        bool: True se sono stati trovati aggiornamenti, False altrimenti
    """
    try:
        # Se non esiste il file locale, scaricalo comunque
        if not os.path.exists(LOCAL_JSON):
            if safe_download_file(REMOTE_URL, LOCAL_JSON):
                return True
            return False
            
        # Crea backup se non esiste
        if os.path.exists(LOCAL_JSON) and not os.path.exists(BACKUP_JSON):
            shutil.copy(LOCAL_JSON, BACKUP_JSON)
            
        # Controlla ETag per aggiornamenti
        req = urllib.request.Request(REMOTE_URL, method='HEAD')
        response = urllib.request.urlopen(req, timeout=10)
        current_etag = response.headers.get('ETag', '').strip('"')
        last_etag = ""
        
        if os.path.exists(LAST_ETAG_FILE):
            with open(LAST_ETAG_FILE, 'r') as f:
                last_etag = f.read().strip()
                
        # Se non c'è ETag salvato, scarica comunque
        if not last_etag:
            if safe_download_file(REMOTE_URL, LOCAL_JSON):
                with open(LAST_ETAG_FILE, 'w') as f:
                    f.write(current_etag)
                return True
            return False
            
        # Se ETag è cambiato, scarica nuovo file
        if current_etag and current_etag != last_etag:
            if safe_download_file(REMOTE_URL, LOCAL_JSON):
                with open(LAST_ETAG_FILE, 'w') as f:
                    f.write(current_etag)
                xbmcgui.Dialog().notification(
                    ADDON_NAME,
                    "Nuovi repository disponibili!",
                    ADDON_ICON,
                    5000
                )
                return True
        return False
        
    except urllib.error.HTTPError as e:
        error_msg = f"Errore HTTP {e.code}: {e.reason}"
        log(f"Controllo aggiornamenti fallito: {error_msg}", xbmc.LOGERROR)
        
        if e.code == 403:
            xbmcgui.Dialog().notification(
                ADDON_NAME,
                "Hai raggiunto il limite di richieste a GitHub!",
                xbmcgui.NOTIFICATION_ERROR,
                7000
            )
            xbmcgui.Dialog().ok(
                ADDON_NAME,
                "Errore 403: Accesso negato\n\n"
                "Hai superato il limite di richieste a GitHub.\n\n"
                "Soluzioni possibili:\n"
                "1. Riavvia il modem per ottenere un nuovo IP\n"
                "2. Prova di nuovo tra 1-2 ore\n"
                "3. Contatta il provider se il problema persiste\n\n"
                "GitHub limita le richieste per proteggere i suoi server."
            )
        elif e.code == 404:
            xbmcgui.Dialog().notification(
                ADDON_NAME,
                "URL non trovato! Verifica le impostazioni",
                xbmcgui.NOTIFICATION_ERROR,
                5000
            )
        else:
            xbmcgui.Dialog().notification(
                ADDON_NAME,
                f"Errore {e.code} durante l'accesso a GitHub",
                xbmcgui.NOTIFICATION_ERROR,
                5000
            )
        return False
        
    except urllib.error.URLError as e:
        log(f"Errore di connessione: {str(e)}", xbmc.LOGERROR)
        xbmcgui.Dialog().notification(
            ADDON_NAME,
            "Errore di connessione a GitHub",
            xbmcgui.NOTIFICATION_ERROR,
            5000
        )
        return False
        
    except Exception as e:
        log(f"Controllo aggiornamenti fallito: {traceback.format_exc()}", xbmc.LOGERROR)
        xbmcgui.Dialog().notification(
            ADDON_NAME,
            "Errore sconosciuto durante il controllo aggiornamenti",
            xbmcgui.NOTIFICATION_ERROR,
            5000
        )
        return False