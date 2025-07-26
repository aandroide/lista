import os
import xbmc
import xbmcaddon
import xbmcvfs
import xbmcgui
import shutil
from . import sources_manager
from .version_utils import (get_release_channel, parse_addon_xml_version, 
                           get_version_from_zip, is_version_greater, are_versions_equal,
                           log_info, log_error)

ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo('id')
ADDON_NAME = ADDON.getAddonInfo('name')
ICON_PATH = xbmcvfs.translatePath(
    os.path.join('special://home/addons', ADDON_ID, ADDON.getAddonInfo('icon'))
)

# Configurazione installazioni temporanee
TEMP_INSTALLS = [
    {
        "addon_id": "plugin.video.youtube",
        "source_name": "YouTube Install",
        "virtual_path": "special://profile/addon_data/youtube_install/"
    },
    {
        "addon_id": "script.trakt",
        "source_name": "Trakt Install",
        "virtual_path": "special://profile/addon_data/trakt_install/"
    }
]

def cleanup_temp_install_folders():
    """Pulizia avanzata solo dopo installazione effettiva"""
    cleaned_something = False
    messages = []
    
    for install in TEMP_INSTALLS:
        addon_id = install["addon_id"]
        source_name = install["source_name"]
        virtual_path = install['virtual_path']
        dest_dir = xbmcvfs.translatePath(virtual_path)
        cleaned_this = False
        
        # Percorsi installazione
        installed_dir = xbmcvfs.translatePath(f"special://home/addons/{addon_id}")
        installed_xml = os.path.join(installed_dir, 'addon.xml')
        
        if not os.path.exists(dest_dir):
            log_info(f"Cartella temporanea non trovata per {addon_id}")
            continue

        # Cerca file ZIP
        zip_files = [f for f in os.listdir(dest_dir)
                     if f.lower().endswith('.zip') and 
                     addon_id.replace('.', '').lower() in f.replace('.', '').replace('-', '').replace('_', '').lower()]
        
        if not zip_files:
            log_info(f"Nessun ZIP trovato per {addon_id} in {dest_dir}")
            continue
            
        log_info(f"Trovati {len(zip_files)} file ZIP per {addon_id}")

        # Se l'addon non è installato, non mostriamo il prompt
        if not os.path.exists(installed_xml):
            log_info(f"{addon_id} non installato, salto la pulizia")
            continue

        # Ottieni info versione installata
        installed_version = parse_addon_xml_version(installed_xml)
        installed_channel = get_release_channel(installed_version)
        log_info(f"Versione installata: {installed_version} ({installed_channel})")
        
        # Ottieni info versione dal primo ZIP
        zip_path = os.path.join(dest_dir, zip_files[0])
        temp_version = get_version_from_zip(zip_path)
        
        if not temp_version:
            log_info(f"Impossibile estrarre versione da {zip_files[0]}")
            continue
            
        temp_channel = get_release_channel(temp_version)
        log_info(f"Versione ZIP: {temp_version} ({temp_channel})")
        
        # Marker per tracciare l'installazione
        marker_path = os.path.join(dest_dir, ".install_prompted")
        already_prompted = os.path.exists(marker_path)
        
        # Determina se mostrare il prompt
        show_prompt = False
        if installed_channel != temp_channel:
            msg = f"Canale diverso disponibile per {addon_id}!\n\n"
            msg += f"Attuale: {installed_version} ({installed_channel})\n"
            msg += f"Disponibile: {temp_version} ({temp_channel})"
            show_prompt = True
        elif not are_versions_equal(installed_version, temp_version):
            msg = f"Aggiornamento disponibile per {addon_id}!\n\n"
            msg += f"Attuale: {installed_version}\n"
            msg += f"Nuova: {temp_version}"
            show_prompt = True
        
        # Mostra il prompt solo se necessario e non già mostrato
        if show_prompt and not already_prompted:
            if xbmcgui.Dialog().yesno(
                ADDON_NAME,
                msg,
                yeslabel="Installa manualmente",
                nolabel="Ignora"
            ):
                # Aggiunge sorgente
                fake_repo = {
                    "name": source_name,
                    "url": virtual_path
                }
                
                if sources_manager.add_source_to_xml(fake_repo):
                    log_info(f"Aggiunta sorgente {source_name}")
                
                # Apre installazione
                xbmc.executebuiltin('InstallFromZip')
                
                # Scrittura marker per indicare che abbiamo mostrato il prompt
                try:
                    with open(marker_path, 'w') as marker:
                        marker.write("prompt_shown")
                    log_info(f"Marker creato per tracciare il prompt")
                except Exception as e:
                    log_error(f"Errore creazione marker: {e}")
                
                # Istruzioni utente
                xbmcgui.Dialog().ok(
                    ADDON_NAME,
                    f"Passi per installare {addon_id}:\n\n"
                    "1. Nella finestra apparsa, seleziona:\n"
                    f"   » '{source_name}'\n\n"
                    "2. Scegli il file ZIP:\n"
                    f"   » {os.path.basename(zip_path)}\n\n"
                    "3. Conferma l'installazione"
                )
        
        # PULIZIA: esegui solo se l'utente ha installato la versione
        install_success_marker = os.path.join(dest_dir, ".install_success")
        
        # VERIFICA DIRETTA SENZA ATTENDERE MARKER
        if os.path.exists(installed_xml):
            current_version = parse_addon_xml_version(installed_xml)
            if are_versions_equal(current_version, temp_version):
                # Controlla se è necessario creare il marker
                if not os.path.exists(install_success_marker):
                    try:
                        with open(install_success_marker, 'w') as f:
                            f.write(temp_version)
                        log_info(f"Installazione rilevata per {addon_id} {temp_version}")
                    except Exception as e:
                        log_error(f"Errore creazione marker di successo: {e}")
                
                # Esegui pulizia immediata
                try:
                    # Rimuove sorgente
                    fake_repo = {
                        "name": source_name,
                        "url": virtual_path
                    }
                    
                    if sources_manager.remove_source_from_xml(fake_repo):
                        msg = f"Rimossa sorgente {source_name} da sources.xml"
                        messages.append(msg)
                        cleaned_this = True

                    # Rimuove l'intera cartella temporanea
                    try:
                        shutil.rmtree(dest_dir)
                        log_info(f"Rimossa completamente la cartella temporanea: {dest_dir}")
                        
                        msg = f"Pulizia completata per {source_name}"
                        messages.append(msg)
                        cleaned_this = True
                    except Exception as e:
                        error_msg = f"Errore rimozione cartella {dest_dir}: {e}"
                        messages.append(error_msg)
                        log_error(error_msg)
                except Exception as e:
                    log_error(f"Errore durante la pulizia: {e}")
        
        # Pulisci se esiste il marker di successo (compatibilità con vecchie installazioni)
        elif os.path.exists(install_success_marker):
            try:
                # Rimuove sorgente
                fake_repo = {
                    "name": source_name,
                    "url": virtual_path
                }
                
                if sources_manager.remove_source_from_xml(fake_repo):
                    msg = f"Rimossa sorgente {source_name} da sources.xml"
                    messages.append(msg)
                    cleaned_this = True

                # Rimuove l'intera cartella temporanea
                try:
                    shutil.rmtree(dest_dir)
                    log_info(f"Rimossa completamente la cartella temporanea: {dest_dir}")
                    
                    msg = f"Pulizia completata per {source_name}"
                    messages.append(msg)
                    cleaned_this = True
                except Exception as e:
                    error_msg = f"Errore rimozione cartella {dest_dir}: {e}"
                    messages.append(error_msg)
                    log_error(error_msg)
            except Exception as e:
                log_error(f"Errore durante la pulizia: {e}")

        if cleaned_this:
            cleaned_something = True

    # Notifica finale
    if cleaned_something:
        summary = "Operazioni completate:\n" + "\n".join(f"- {msg}" for msg in messages)
        
        xbmcgui.Dialog().notification(
            ADDON_NAME,
            "Pulizia completata",
            ICON_PATH,
            5000
        )
        
        if xbmcgui.Dialog().yesno(
            ADDON_NAME,
            f"{summary}\n\nRiavviare Kodi per applicare le modifiche?",
            yeslabel="Riavvia ora",
            nolabel="Più tardi"
        ):
            xbmc.executebuiltin('RestartApp')

    return cleaned_something
