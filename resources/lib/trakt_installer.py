# -*- coding: utf-8 -*-
"""
Plugin Trakt Installer
Scarica la release .zip dello script.trakt
nella cartella 'special://profile/addon_data/trakt_install',
e mostra la versione scaricata.
"""

import json
import urllib.request
import xbmc
import xbmcgui
import xbmcaddon
import xbmcvfs
import os
import re
import traceback
from resources.lib.utils import log
from resources.lib import sources_manager

ADDON = xbmcaddon.Addon()
ADDON_NAME = ADDON.getAddonInfo('name')

def install_trakt_addon():
    """
    Scarica lo zip di Trakt in special://profile/addon_data/trakt_install
    e mostra la versione scaricata.
    """
    try:
        result = get_latest_trakt_url()
        if not result:
            raise Exception("Nessuna release Trakt trovata")
        
        zip_url, version = result
        log(f"Trovata versione Trakt: {version}", xbmc.LOGINFO)

        # Percorso virtuale scelto
        virtual_path = "special://profile/addon_data/trakt_install"
        dest_dir = xbmcvfs.translatePath(virtual_path)
        xbmcvfs.mkdirs(dest_dir)

        # Registra cartella come fonte visibile
        fake_repo = {
            "name": "Trakt Install",
            "url": virtual_path + '/'
        }
        sources_manager.add_source_to_xml(fake_repo)

        # Estrai il nome file dall'URL o costruiscilo
        if zip_url.endswith('.zip'):
            zip_name = os.path.basename(zip_url)
        else:
            # Costruisci un nome file significativo
            zip_name = f"script.trakt-{version}.zip"

        dest_path = os.path.join(dest_dir, zip_name)

        # Controllo esistenza file
        file_exists = os.path.exists(dest_path)
        log(f"Controllo esistenza file: {dest_path} -> {'esiste' if file_exists else 'non esiste'}", xbmc.LOGINFO)

        if file_exists:
            # Messaggio che il file esiste già
            if xbmcgui.Dialog().yesno(
                "Trakt Addon",
                f"Il file esiste già:\n[COLOR yellow]{zip_name}[/COLOR]\n\n"
                "Vuoi sovrascriverlo?",
                yeslabel="Sì, Sovrascrivi",
                nolabel="Annulla"
            ):
                os.remove(dest_path)
                log(f"File esistente rimosso: {dest_path}", xbmc.LOGINFO)
            else:
                return False

        # Scarica ZIP
        req = urllib.request.Request(zip_url)
        req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)')
        
        with urllib.request.urlopen(req) as response:
            if response.getcode() != 200:
                raise Exception(f"Errore nel download: {response.getcode()}")
            
            # Ottieni l'URL finale dopo i redirect
            final_url = response.geturl()
            if final_url != zip_url:
                log(f"Reindirizzato a: {final_url}", xbmc.LOGINFO)
                if final_url.endswith('.zip'):
                    zip_name = os.path.basename(final_url)
                    dest_path = os.path.join(dest_dir, zip_name)
            
            with open(dest_path, 'wb') as f:
                f.write(response.read())

        # PRIMO DIALOG: Messaggio di conferma download con versione
        xbmcgui.Dialog().ok(
            "Trakt Addon",
            f"Scaricata versione [COLOR lime]{version}[/COLOR]:\n[COLOR yellow]{zip_name}[/COLOR]\n\n"
            "Dopo il riavvio vai su:\n"
            "[COLOR lime]Add-on → Installa da file zip → Trakt Install[/COLOR]"
        )

        # SECONDO DIALOG: Richiesta di riavvio
        if xbmcgui.Dialog().yesno(
            "Trakt Addon",
            "Riavviare Kodi ora per completare l'installazione?",
            yeslabel="Sì, Riavvia",
            nolabel="Più tardi"
        ):
            xbmc.executebuiltin("RestartApp")
        else:
            xbmcgui.Dialog().notification(
                "Trakt Addon",
                "Ricorda di riavviare per vedere la cartella",
                xbmcgui.NOTIFICATION_INFO,
                3000
            )

        return True

    except Exception as e:
        log(f"TraktInstaller error: {traceback.format_exc()}", xbmc.LOGERROR)
        xbmcgui.Dialog().notification(
            "Trakt Addon",
            f"Errore durante l'installazione: {str(e)}",
            xbmcgui.NOTIFICATION_ERROR,
            5000
        )
        return False


def get_latest_trakt_url():
    """
    Restituisce l'URL zip e la versione dell'ultima release di Trakt
    """
    # URL API per le release
    api_url = "https://api.github.com/repos/trakt/script.trakt/releases"
    
    try:
        req = urllib.request.Request(api_url)
        req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)')
        
        with urllib.request.urlopen(req, timeout=15) as resp:
            if resp.getcode() != 200:
                raise Exception(f"Errore API GitHub: {resp.getcode()}")
            releases = json.loads(resp.read().decode('utf-8'))
    except Exception as e:
        raise Exception(f"Errore API GitHub: {str(e)}")
    
    # Filtra solo release stabili (non prerelease)
    stable_releases = [r for r in releases if not r.get('prerelease', False)]
    
    if not stable_releases:
        raise Exception("Nessuna release stabile disponibile")
    
    # Ordina per data di pubblicazione (più recente prima)
    stable_releases.sort(
        key=lambda r: r.get('published_at', '0'), 
        reverse=True
    )
    
    # Cerca nella release più recente un asset ZIP valido
    latest_release = stable_releases[0]
    version = latest_release.get("tag_name", "unknown")
    
    # Pulisci la versione
    version = re.sub(r'^v[\.]*', '', version, flags=re.IGNORECASE)
    
    # Cerca un asset ZIP
    zip_url = None
    for asset in latest_release.get("assets", []):
        name = asset["name"].lower()
        if name.endswith(".zip"):
            zip_url = asset["browser_download_url"]
            break
    
    # Fallback allo zipball_url se non trovato (source code snapshot)
    if not zip_url:
        zip_url = latest_release.get("zipball_url", "")
    
    if not zip_url:
        raise Exception("Nessun URL download trovato")
    
    return (zip_url, version)