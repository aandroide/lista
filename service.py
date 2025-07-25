# -*- coding: utf-8 -*-
"""
Repo_Addon_installer-Service per Kodi addon: sincronizza i file remoti
- Esegue sync solo se c'è un nuovo commit
- Scarica file mancanti o modificati
- Rimuove file locali non più remoti
- Notifica solo se ci sono aggiornamenti, mostrando il commit
- Pulizia automatica delle installazioni temporanee
"""

import xbmc, xbmcaddon, xbmcvfs, xbmcgui
import urllib.request, urllib.error
import json, os, shutil
from resources.lib import sources_manager

# --- Configurazione Addon ---
ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo('id')
ADDON_NAME = ADDON.getAddonInfo('name')
ICON_PATH = xbmcvfs.translatePath(
    os.path.join('special://home/addons', ADDON_ID, ADDON.getAddonInfo('icon'))
)

# Percorsi
PROFILE_PATH = xbmcvfs.translatePath(ADDON.getAddonInfo('profile'))
os.makedirs(PROFILE_PATH, exist_ok=True)
LAST_COMMIT_FILE = os.path.join(PROFILE_PATH, 'last_commit.txt')
ADDON_PATH = xbmcvfs.translatePath(os.path.join('special://home/addons', ADDON_ID))

# File da preservare
IGNORE_FILES = {'.firstrun'}

# Impostazioni GitHub
github_user = ADDON.getSetting('github_user')
github_repo = ADDON.getSetting('github_repo')
github_branch = ADDON.getSetting('github_branch') or 'main'

# --- Helper Generici ---
def log_info(msg):
    xbmc.log(f"[Repo_Addon_installer-Service] {msg}", xbmc.LOGINFO)

def log_error(msg):
    xbmc.log(f"[Repo_Addon_installer-Service] {msg}", xbmc.LOGERROR)

def handle_http_error(e):
    """Gestione avanzata errori HTTP con notifiche utente"""
    if e.code == 403:
        xbmcgui.Dialog().notification(
            ADDON_NAME,
            "Limite richieste GitHub raggiunto!",
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

def github_api_request(path, timeout=10):
    """Chiamata centralizzata alle API GitHub con gestione errori avanzata"""
    url = f"https://api.github.com/repos/{github_user}/{github_repo}{path}"
    try:
        resp = urllib.request.urlopen(url, timeout=timeout)
        if resp.getcode() != 200:
            log_error(f"API code inaspettato {resp.getcode()} per {url}")
            return None
        return json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        return handle_http_error(e)
    except Exception as e:
        log_error(f"richiesta API fallita {url}: {e}")
    return None

# --- Funzioni helper per gestione versioni ---
def parse_addon_xml_version(addon_xml_path):
    """Parsa addon.xml per estrarre la versione"""
    try:
        import xml.etree.ElementTree as ET
        tree = ET.parse(addon_xml_path)
        root = tree.getroot()
        return root.get('version', '0.0.0')
    except Exception as e:
        log_error(f"Errore parsing addon.xml: {e}")
    return '0.0.0'

def get_installed_addon_version(addon_id):
    """Ottiene la versione installata di un addon"""
    try:
        return xbmcaddon.Addon(addon_id).getAddonInfo('version')
    except:
        return '0.0.0'

def is_version_greater(v1, v2):
    """Confronta due versioni nel formato semantico (major.minor.patch)"""
    def parse_version(v):
        parts = []
        for part in v.split('.'):
            try:
                parts.append(int(part))
            except ValueError:
                # Gestione componenti non numeriche
                parts.append(0)
        # Completa con zeri se mancanti
        while len(parts) < 3:
            parts.append(0)
        return parts
    
    v1_parts = parse_version(v1)
    v2_parts = parse_version(v2)
    
    return v1_parts > v2_parts

def are_versions_equal(v1, v2):
    """Controlla se due versioni sono identiche"""
    def parse_version(v):
        parts = []
        for part in v.split('.'):
            try:
                parts.append(int(part))
            except ValueError:
                parts.append(0)
        while len(parts) < 3:
            parts.append(0)
        return parts
    
    return parse_version(v1) == parse_version(v2)

# --- Gestione Commit ---
def read_last_commit():
    """Legge l'ultimo commit memorizzato localmente"""
    try:
        if os.path.exists(LAST_COMMIT_FILE):
            with open(LAST_COMMIT_FILE, 'r') as f:
                return f.read().strip()
    except Exception as e:
        log_error(f"lettura ultimo commit: {e}")
    return ''

def write_last_commit(sha):
    """Salva lo SHA del commit corrente"""
    try:
        with open(LAST_COMMIT_FILE, 'w') as f:
            f.write(sha)
    except Exception as e:
        log_error(f"scrittura ultimo commit: {e}")

# --- Remote Data ---
def get_remote_commit():
    """Ottiene l'ultimo commit SHA dal ramo remoto"""
    data = github_api_request(f"/commits/{github_branch}")
    return data.get('sha', '') if data else ''

def get_remote_file_list():
    """Ottiene la lista completa dei file dal repository remoto"""
    data = github_api_request(f"/git/trees/{github_branch}?recursive=1")
    if not data:
        return []
    return [item['path'] for item in data.get('tree', []) if item.get('type') == 'blob']

# --- Sincronizzazione File ---
def sync_orphan_files(remote_paths):
    """Rimuove i file locali non presenti nel repository remoto"""
    for root, _, files in os.walk(ADDON_PATH, topdown=False):
        for name in files:
            full_path = os.path.join(root, name)
            rel_path = os.path.relpath(full_path, ADDON_PATH).replace('\\', '/')
            
            if rel_path in IGNORE_FILES:
                continue
                
            if rel_path not in remote_paths:
                try:
                    os.remove(full_path)
                    log_info(f"Rimosso file orfano: {rel_path}")
                except Exception as e:
                    log_error(f"Errore rimozione file orfano {rel_path}: {e}")
        
        # Rimuove cartelle vuote
        if not os.listdir(root) and root != ADDON_PATH:
            try:
                os.rmdir(root)
                log_info(f"Rimossa cartella vuota: {os.path.relpath(root, ADDON_PATH)}")
            except Exception as e:
                log_error(f"Errore rimozione cartella vuota: {e}")

def download_content(rel_path):
    """Scarica il contenuto di un file dal repository"""
    url = f"https://raw.githubusercontent.com/{github_user}/{github_repo}/{github_branch}/{rel_path}"
    try:
        with urllib.request.urlopen(url, timeout=20) as response:
            return response.read()
    except urllib.error.HTTPError as e:
        handle_http_error(e)
    except Exception as e:
        log_error(f"Errore download {rel_path}: {e}")
    return None

def sync_all(remote_paths):
    """Sincronizza tutti i file con il repository remoto"""
    for rel_path in remote_paths:
        local_path = os.path.join(ADDON_PATH, rel_path)
        remote_content = download_content(rel_path)
        
        if remote_content is None:
            continue
            
        # Controlla se il file esiste ed è identico
        file_exists = os.path.exists(local_path)
        if file_exists:
            try:
                with open(local_path, 'rb') as local_file:
                    if local_file.read() == remote_content:
                        continue
            except Exception as e:
                log_error(f"Errore lettura file locale {rel_path}: {e}")
        
        # Crea directory se necessario e scrive il file
        try:
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            with open(local_path, 'wb') as local_file:
                local_file.write(remote_content)
            log_info(f"File {'aggiornato' if file_exists else 'scaricato'}: {rel_path}")
        except Exception as e:
            log_error(f"Errore scrittura file {rel_path}: {e}")
    
    # Rimuove i file orfani
    sync_orphan_files(remote_paths)

# --- Pulizia Origini Temporanee con verifica versione ---
def cleanup_temp_install_folders():
    """Pulizia avanzata con controllo versione e aggiornamento"""
    cleaned_something = False
    messages = []
    
    # Configurazione per le installazioni temporanee
    temp_installs = [
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
    
    for install in temp_installs:
        addon_id = install["addon_id"]
        source_name = install["source_name"]
        dest_dir = xbmcvfs.translatePath(install['virtual_path'])
        addon_xml_path = os.path.join(dest_dir, 'addon.xml')
        cleaned_this = False
        
        # Verifica se l'addon è installato
        is_installed = xbmc.getCondVisibility(f"System.HasAddon({addon_id})")
        
        # Verifica se esiste la cartella temporanea
        temp_folder_exists = os.path.exists(dest_dir)
        temp_version_available = temp_folder_exists and os.path.exists(addon_xml_path)
        
        # Se la cartella temporanea esiste ma l'addon non è installato
        if temp_folder_exists and not is_installed:
            log_info(f"Cartella temporanea presente per {addon_id} ma addon non installato - Mantenuta per installazione futura")
            continue  # Salta alla prossima iterazione senza pulire
            
        # Se l'addon è installato procedi con i controlli
        if is_installed:
            # Ottieni versione installata
            installed_version = get_installed_addon_version(addon_id)
            log_info(f"Versione installata di {addon_id}: {installed_version}")
            
            # Ottieni versione nella cartella temporanea
            temp_version = '0.0.0'
            if temp_version_available:
                temp_version = parse_addon_xml_version(addon_xml_path)
                log_info(f"Versione temporanea di {addon_id}: {temp_version}")
            
            # Controlla se è disponibile una versione più nuova
            update_available = temp_version_available and is_version_greater(temp_version, installed_version)
            
            # Controlla se le versioni sono identiche
            versions_equal = temp_version_available and are_versions_equal(temp_version, installed_version)
            
            # Controlla se la versione installata è maggiore di quella temporanea
            installed_is_newer = temp_version_available and is_version_greater(installed_version, temp_version)
            
            # Gestione aggiornamento
            if update_available:
                msg = f"Disponibile aggiornamento {addon_id}: {installed_version} → {temp_version}"
                messages.append(msg)
                log_info(msg)
                
                # Prompt per aggiornamento
                if xbmcgui.Dialog().yesno(
                    ADDON_NAME,
                    f"Nuova versione disponibile per {addon_id}!\n\n"
                    f"Versione attuale: {installed_version}\n"
                    f"Nuova versione: {temp_version}\n\n"
                    "Vuoi aggiornare ora?",
                    yeslabel="Aggiorna",
                    nolabel="Ignora"
                ):
                    # Copia i file dalla cartella temporanea all'addon
                    addon_path = xbmcvfs.translatePath(f"special://home/addons/{addon_id}")
                    try:
                        # Copia ricorsiva sovrascrivendo i file
                        if os.path.exists(addon_path):
                            shutil.rmtree(addon_path)
                        shutil.copytree(dest_dir, addon_path)
                        
                        msg = f"Aggiornato {addon_id} alla versione {temp_version}"
                        messages.append(msg)
                        log_info(msg)
                        cleaned_this = True
                        
                        # Dopo l'aggiornamento, rimuovi la cartella temporanea
                        try:
                            shutil.rmtree(dest_dir, ignore_errors=True)
                            messages.append(f"Rimossa cartella temporanea {source_name}")
                        except Exception as e:
                            log_error(f"Errore rimozione cartella temporanea: {e}")
                    except Exception as e:
                        error_msg = f"Errore aggiornamento {addon_id}: {e}"
                        messages.append(error_msg)
                        log_error(error_msg)
            
            # Pulizia quando le versioni sono identiche o quella installata è più nuova
            elif temp_version_available and (versions_equal or installed_is_newer):
                # Rimuove da sources.xml
                fake_repo = {
                    "name": source_name,
                    "url": install['virtual_path']
                }
                
                if sources_manager.remove_source_from_xml(fake_repo):
                    msg = f"Rimossa sorgente {source_name} da sources.xml"
                    messages.append(msg)
                    log_info(msg)
                    cleaned_this = True

                # Rimuove cartella fisica
                if os.path.exists(dest_dir):
                    try:
                        shutil.rmtree(dest_dir, ignore_errors=True)
                        msg = f"Rimossa cartella temporanea {source_name}"
                        messages.append(msg)
                        log_info(msg)
                        cleaned_this = True
                    except Exception as e:
                        error_msg = f"Errore rimozione cartella temporanea: {e}"
                        messages.append(error_msg)
                        log_error(error_msg)
                else:
                    log_info(f"Cartella temporanea non trovata: {dest_dir}")

        if cleaned_this:
            cleaned_something = True

    # Notifica e richiedi riavvio
    if cleaned_something:
        log_info("Pulizia/aggiornamento completato")
        summary = "Operazioni completate:\n" + "\n".join(f"- {msg}" for msg in messages)
        
        xbmcgui.Dialog().notification(
            ADDON_NAME,
            "Pulizia/aggiornamento completato",
            ICON_PATH,
            5000
        )
        
        if xbmcgui.Dialog().yesno(
            ADDON_NAME,
            f"{summary}\n\nRiavviare Kodi per applicare le modifiche?",
            yeslabel="Riavvia ora",
            nolabel="Più tardi"
        ):
            xbmc.executebuiltin("RestartApp")
    else:
        log_info("Nessuna operazione di pulizia/aggiornamento necessaria")

# --- Main Service Functions ---
def check_self_update():
    """Controlla e applica aggiornamenti dal repository"""
    if not github_user or not github_repo:
        log_error("Parametri GitHub mancanti nelle impostazioni")
        return
    
    remote_sha = get_remote_commit()
    if not remote_sha:
        return
    
    last_sha = read_last_commit()
    if remote_sha == last_sha:
        log_info("Nessun aggiornamento disponibile")
        return
    
    log_info(f"Trovato nuovo commit: {remote_sha}")
    remote_paths = get_remote_file_list()
    
    if not remote_paths:
        log_error("Nessun file trovato nel repository remoto")
        return
    
    try:
        sync_all(remote_paths)
        write_last_commit(remote_sha)
        xbmcgui.Dialog().notification(
            ADDON_NAME,
            f"Addon aggiornato ({remote_sha[:7]})",
            ICON_PATH,
            5000
        )
        log_info("Aggiornamento completato con successo")
    except Exception as e:
        log_error(f"Errore durante la sincronizzazione: {e}")
        xbmcgui.Dialog().notification(
            ADDON_NAME,
            "Errore durante l'aggiornamento!",
            xbmcgui.NOTIFICATION_ERROR,
            5000
        )

if __name__ == '__main__':
    log_info("Servizio avviato")
    check_self_update()
    cleanup_temp_install_folders()
    log_info("Servizio terminato")
