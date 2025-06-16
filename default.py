# -*- coding: utf-8 -*-
import xbmc
import xbmcgui
import xbmcaddon
import xbmcvfs
import os
import json
import urllib.request
import xml.etree.ElementTree as ET
import pyqrcode
import traceback
import shutil
import time
import re
from resources.lib.utils import get_sources, get_github_config, log, safe_download_file, get_existing_sources, remove_physical_repo

ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo('id')
ADDON_NAME = ADDON.getAddonInfo('name')
ADDON_ICON = ADDON.getAddonInfo('icon')
ADDON_PATH = xbmcvfs.translatePath(ADDON.getAddonInfo('path'))
FIRST_RUN_FILE = os.path.join(ADDON_PATH, ".firstrun")
LAST_ETAG_FILE = os.path.join(ADDON_PATH, ".last_etag")
BACKUP_JSON = os.path.join(ADDON_PATH, "resources", "addons_backup.json")
NO_TELEGRAM_IMAGE = os.path.join(ADDON_PATH, "resources", "skins", "default", "media", "no-telegram.png")
# ID esatti dei repository
KODINERDS_REPO_ID = "repository.kodinerds"
SANDMANN_REPO_ID = "repository.sandmann79.plugins"
ELEMENTUM_REPO_ID = "repository.elementumorg"
LOCAL_JSON = os.path.join(ADDON_PATH, 'resources', 'addons.json')

def show_intro_message_once():
    try:
        if not os.path.exists(FIRST_RUN_FILE):
            with open(FIRST_RUN_FILE, 'w') as f:
                f.write("shown")
            xbmcgui.Dialog().ok(ADDON_NAME,
                "Prima di procedere ti consigliamo di unirti ai canali Telegram ufficiali.\n\n"
                "Questo addon non sostituisce le guide ufficiali. Alcuni addon potrebbero necessitare dipendenze aggiuntive.")
    except Exception as e:
        log(f"Errore nel messaggio introduttivo: {str(e)}", xbmc.LOGERROR)

def check_for_updates():
    remote_url = get_github_config()
    try:
        if os.path.exists(LOCAL_JSON) and not os.path.exists(BACKUP_JSON):
            shutil.copy(LOCAL_JSON, BACKUP_JSON)
        req = urllib.request.Request(REMOTE_URL, method='HEAD')
        response = urllib.request.urlopen(req, timeout=10)
        current_etag = response.headers.get('ETag', '').strip('"')
        last_etag = ""
        if os.path.exists(LAST_ETAG_FILE):
            with open(LAST_ETAG_FILE, 'r') as f:
                last_etag = f.read().strip()
        if not last_etag:
            if safe_download_file(REMOTE_URL, LOCAL_JSON):
                with open(LAST_ETAG_FILE, 'w') as f:
                    f.write(current_etag)
                return True
            return False
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
    except Exception as e:
        log(f"Controllo aggiornamenti fallito: {traceback.format_exc()}", xbmc.LOGERROR)
        return False

# Esegui inizializzazioni
show_intro_message_once()

# Controlla aggiornamenti all'avvio
if check_for_updates():
    log("File addons.json aggiornato")
else:
    log("Nessun aggiornamento disponibile")

def is_repo_installed_by_id(repo_id):
    return xbmc.getCondVisibility(f"System.HasAddon({repo_id})") == 1

def is_any_sandmann_repo_installed():
    return any(
        is_repo_installed_by_id(repo_id)
        for repo_id in [
            SANDMANN_REPO_ID,
            "repository.sandmann79",
            "repository.sandmann79s"
        ]
    )

def is_elementum_repo_installed():
    return is_repo_installed_by_id(ELEMENTUM_REPO_ID)

def generate_qr_code(url, name="qr"):
    try:
        qr = pyqrcode.create(url)
        temp_dir = xbmcvfs.translatePath("special://temp")
        image_path = os.path.join(temp_dir, f"{name}_qr.png")
        qr.png(image_path, scale=6)
        return image_path
    except Exception as e:
        log(f"Errore generazione QR: {str(e)}", xbmc.LOGERROR)
        return ""

def add_source_to_xml(repo):
    sources_path = xbmcvfs.translatePath("special://profile/sources.xml")
    name = repo.get("name", "Sconosciuto")
    url = repo.get("url", "")
    if not url:
        log(f"Sorgente '{name}' senza URL", xbmc.LOGWARNING)
        return False
    
    if os.path.exists(sources_path):
        try:
            tree = ET.parse(sources_path)
            root = tree.getroot()
        except:
            root = ET.Element("sources")
            tree = ET.ElementTree(root)
    else:
        root = ET.Element("sources")
        tree = ET.ElementTree(root)
    
    files_node = root.find("files")
    if files_node is None:
        files_node = ET.SubElement(root, "files")
    
    for source in files_node.findall("source"):
        path_elem = source.find('path')
        if path_elem is not None and path_elem.text == url:
            return False
    
    source = ET.SubElement(files_node, "source")
    ET.SubElement(source, "name").text = name
    ET.SubElement(source, "path", pathversion="1").text = url
    ET.SubElement(source, "allowsharing").text = "true"
    
    # Formatta l'XML con indentazione
    def indent(elem, level=0):
        spacer = "  "  # 2 spazi per livello
        indent_prefix = "\n" + level * spacer
        if len(elem):
            if not elem.text or not elem.text.strip():
                elem.text = indent_prefix + spacer
            for child in elem:
                indent(child, level + 1)
            if not child.tail or not child.tail.strip():
                child.tail = indent_prefix
        else:
            if level and (not elem.tail or not elem.tail.strip()):
                elem.tail = indent_prefix
    
    indent(root)  # Applica l'indentazione all'intero XML
    
    try:
        # Scrive l'XML formattato
        xml_str = ET.tostring(root, encoding='utf-8', xml_declaration=True)
        with open(sources_path, 'wb') as f:
            f.write(xml_str)
        return True
    except Exception as e:
        log(f"Errore scrittura sources.xml: {str(e)}", xbmc.LOGERROR)
        return False

def remove_source_from_xml(repo):
    sources_path = xbmcvfs.translatePath("special://profile/sources.xml")
    url = repo.get("url", "")
    if not os.path.exists(sources_path) or not url:
        return False
    try:
        tree = ET.parse(sources_path)
        root = tree.getroot()
        files_node = root.find("files")
        if files_node is None:
            return False
        removed = False
        for source in files_node.findall("source"):
            path_elem = source.find('path')
            if path_elem is not None and path_elem.text == url:
                files_node.remove(source)
                removed = True
                break
        if removed:
            tree.write(sources_path, encoding='utf-8', xml_declaration=True)
            return True
        return False
    except Exception as e:
        log(f"Errore rimozione sorgente da sources.xml: {str(e)}", xbmc.LOGERROR)
        return False

class RepoManagerGUI(xbmcgui.WindowXML):
    def __init__(self, *args, **kwargs):
        super().__init__()
        self.sources = []
        self.selected_index = 0
        self.existing_urls = []
        self.controls = {
            'list': None,
            'title': None,
            'description': None,
            'link': None,
            'qr_image': None
        }

    def onInit(self):
        self.initialize_controls()
        self.load_data()
        self.populate_list()
        self.setFocusId(100)

    def initialize_controls(self):
        self.controls['list']       = self.getControl(100)
        self.controls['title']      = self.getControl(101)
        self.controls['description']= self.getControl(200)
        self.controls['link']       = self.getControl(103)
        self.controls['qr_image']   = self.getControl(300)

    def load_data(self):
        # Carica tutte le sorgenti dal JSON
        sources = get_sources()
        # Controlla lo setting ShowAdult: restituisce "true" o "false"
        show_adult = ADDON.getSetting("ShowAdult") == "true"
        if not show_adult:
            sources = [
                s for s in sources
                if s.get("name") != "Dobbelina repo (Cumination)"
            ]
        self.sources = sources
        self.existing_urls = get_existing_sources()
        log(f"Caricate {len(self.sources)} sorgenti (ShowAdult={show_adult})")

    def is_repo_installed(self, repo):
        name = repo.get("name", "").lower()
        url = repo.get("url", "")
        if "kodinerds" in name:
            return is_repo_installed_by_id(KODINERDS_REPO_ID)
        elif "sandmann" in name:
            return is_any_sandmann_repo_installed()
        elif "elementum" in name:
            return is_elementum_repo_installed()
        else:
            return url in self.existing_urls

    def normalize_folder_name(self, name):
        """
        Normalizza i nomi delle cartelle in modo intelligente:
        - Rimuove parole comuni ridondanti
        - Accorcia i nomi lunghi
        - Mantiene le parti significative
        """
        # Rimuovi parole chiave ridondanti
        remove_words = ["repo", "repository", "addon", "per", "l'", "di", "da", "e"]
        
        # Mappa sostituzioni specifiche
        replacements = {
            "themoviebd": "tmdb",
            "helper": "hlp",
            "artic": "art",
            "netflix": "nx",
            "amazon": "az",
            "vod": "video",
            "cumination": "cumi",
            "elementum": "elem"
        }
        
        # Sostituzioni specifiche
        for key, value in replacements.items():
            name = name.replace(key, value)
        
        # Rimuovi parole comuni
        words = name.split()
        filtered_words = [word for word in words if word.lower() not in remove_words]
        
        # Unisci e sostituisci caratteri speciali
        normalized = "_".join(filtered_words)
        normalized = re.sub(r'[^a-z0-9]', '_', normalized.lower())
        normalized = re.sub(r'_+', '_', normalized).strip('_')
        
        # Accorcia se troppo lungo
        if len(normalized) > 25:
            parts = normalized.split('_')
            if len(parts) > 1:
                # Prendi le prime lettere di ogni parte
                normalized = "".join(part[0] for part in parts)
            else:
                normalized = normalized[:15]
        
        return normalized

    def create_icon_folder_if_missing(self, folder_path):
        """Crea la cartella per l'icona se non esiste"""
        if not os.path.exists(folder_path):
            try:
                os.makedirs(folder_path)
                log(f"Cartella icona creata: {folder_path}")
            except Exception as e:
                log(f"Errore creazione cartella icona: {str(e)}", xbmc.LOGERROR)

    def populate_list(self):
        if not self.controls['list']:
            return
        self.controls['list'].reset()
        if not self.sources:
            item = xbmcgui.ListItem("Nessun repository disponibile")
            self.controls['list'].addItem(item)
            return

        icons_base_path = os.path.join(ADDON_PATH, 'resources', 'icone')
        
        # Crea la cartella base icone se manca
        if not os.path.exists(icons_base_path):
            try:
                os.makedirs(icons_base_path)
                log(f"Cartella icone principale creata: {icons_base_path}")
            except Exception as e:
                log(f"Errore creazione cartella icone: {str(e)}", xbmc.LOGERROR)
        
        # Percorso dell'icona di default (potrebbe non esistere)
        default_icon = os.path.join(icons_base_path, 'default.png')

        for src in self.sources:
            folder_name = self.normalize_folder_name(src["name"])
            folder_path = os.path.join(icons_base_path, folder_name)
            
            # Crea la cartella specifica per questo repo
            self.create_icon_folder_if_missing(folder_path)
            
            icon_path = None
            if os.path.exists(folder_path) and os.path.isdir(folder_path):
                for icon_file in os.listdir(folder_path):
                    if icon_file.lower().startswith('icon'):
                        icon_path = os.path.join(folder_path, icon_file)
                        break

            # Se non trovata, usa l'icona di default se esiste
            if not icon_path and os.path.exists(default_icon):
                icon_path = default_icon

            item = xbmcgui.ListItem(src["name"])
            if icon_path and os.path.exists(icon_path):
                item.setArt({'icon': icon_path})
            item.setProperty('name', src.get("name", ""))
            item.setProperty('description', src.get("description", ""))
            item.setProperty('telegram', src.get("telegram", ""))
            installed = self.is_repo_installed(src)
            item.setProperty("checked", "true" if installed else "false")
            item.setProperty("action_label", "Rimuovi" if installed else "Aggiungi")
            self.controls['list'].addItem(item)

        if self.sources:
            self.controls['list'].selectItem(0)
            self.selected_index = 0
            self.update_display()

    def update_display(self):
        if not self.sources or self.selected_index >= len(self.sources):
            return
        repo = self.sources[self.selected_index]
        self.controls['title'].setLabel(repo.get("name", ""))
        self.controls['description'].setText(repo.get("description", ""))
        telegram_url = repo.get("telegram", "")
        if telegram_url:
            self.controls['link'].setLabel(telegram_url)
        else:
            self.controls['link'].setLabel("Nessun canale Telegram disponibile")
        if telegram_url:
            qr_path = generate_qr_code(telegram_url, repo["name"])
        else:
            qr_path = NO_TELEGRAM_IMAGE
        self.controls['qr_image'].setImage(qr_path)

    def onAction(self, action):
        action_id = action.getId()
        if action_id in [xbmcgui.ACTION_NAV_BACK, xbmcgui.ACTION_PREVIOUS_MENU]:
            self.close()
            return
        if self.getFocusId() == 100:
            new_index = self.controls['list'].getSelectedPosition()
            if new_index != self.selected_index and new_index < len(self.sources):
                self.selected_index = new_index
                self.update_display()

    def onClick(self, controlId):
        if controlId == 100:
            self.selected_index = self.controls['list'].getSelectedPosition()
            self.update_display()
            if self.selected_index < len(self.sources):
                repo = self.sources[self.selected_index]
                if self.is_repo_installed(repo):
                    self.uninstall_single(repo, show_dialog=True)
                else:
                    self.install_single(repo, show_dialog=True)
        elif controlId == 500:
            self.install_all()
        elif controlId == 202:
            xbmc.executebuiltin("ActivateWindow(filemanager)")
        elif controlId == 203:
            xbmc.executebuiltin('InstallFromZip()')
        elif controlId == 600:
            self.refresh_list()
        elif controlId == 700:  # Nuovo pulsante "Rimuovi tutti"
            self.uninstall_all()

    def refresh_list(self):
        if check_for_updates():
            self.load_data()
            self.populate_list()
            xbmcgui.Dialog().notification(ADDON_NAME, "Lista aggiornata!", ADDON_ICON, 3000)

    def install_all(self):
        added_count = 0
        skipped_count = 0
        progress = xbmcgui.DialogProgress()
        progress.create(ADDON_NAME, "Installazione in corso...")
        total = len(self.sources)
        for i, repo in enumerate(self.sources):
            if progress.iscanceled():
                break
            repo_name = repo.get("name", "Sconosciuto")
            progress.update((i * 100) // total, f"Elaborazione: {repo_name}")
            if self.is_repo_installed(repo):
                skipped_count += 1
                continue
            result = self.install_single(repo, show_dialog=False)
            if result:
                added_count += 1
            else:
                skipped_count += 1
        progress.close()
        self.load_data()
        self.populate_list()
        xbmcgui.Dialog().ok(
            ADDON_NAME,
            f"Aggiunta completata:\n[COLOR=lime]{added_count}[/COLOR] sorgenti nuove\n[COLOR=grey]{skipped_count}[/COLOR] già presenti"
        )
        if added_count > 0:
            if xbmcgui.Dialog().yesno(ADDON_NAME, "Riavviare Kodi ora?", yeslabel="Sì", nolabel="No"):
                xbmc.executebuiltin("RestartApp")
            else:
                xbmcgui.Dialog().notification(ADDON_NAME, "Riavvio richiesto per applicare le modifiche", ADDON_ICON, 3000)

    def uninstall_all(self):
        # Conferma con l'utente
        if not xbmcgui.Dialog().yesno(
            ADDON_NAME, 
            "Vuoi davvero rimuovere TUTTE le sorgenti?\n\n"
            "Questa operazione rimuoverà tutte le sorgenti e i repository installati.",
            yeslabel="Rimuovi Tutto",
            nolabel="Annulla"
        ):
            return
        removed_count = 0
        error_count = 0
        kodinerds_removed = False
        sandmann_removed = False
        elementum_removed = False
        progress = xbmcgui.DialogProgress()
        progress.create(ADDON_NAME, "Rimozione in corso...")
        total = len(self.sources)
        for i, repo in enumerate(self.sources):
            if progress.iscanceled():
                break
            repo_name = repo.get("name", "Sconosciuto")
            progress.update((i * 100) // total, f"Rimozione: {repo_name}")
            # Rimuovi sorgente da sources.xml
            if not self.is_repo_installed(repo):
                continue
            name = repo.get("name", "").lower()
            try:
                # Repository normali
                if not ("kodinerds" in name or "sandmann" in name or "elementum" in name):
                    if remove_source_from_xml(repo):
                        removed_count += 1
                # Repository speciali (Kodinerds/Sandmann/Elementum)
                else:
                    # Kodinerds
                    if "kodinerds" in name and not kodinerds_removed:
                        if remove_physical_repo(KODINERDS_REPO_ID):
                            removed_count += 1
                            kodinerds_removed = True
                    # Sandmann
                    if "sandmann" in name and not sandmann_removed:
                        for repo_id in [SANDMANN_REPO_ID, "repository.sandmann79", "repository.sandmann79s"]:
                            if remove_physical_repo(repo_id):
                                removed_count += 1
                        sandmann_removed = True
                    # Elementum
                    if "elementum" in name and not elementum_removed:
                        if remove_physical_repo(ELEMENTUM_REPO_ID):
                            removed_count += 1
                            elementum_removed = True
            except Exception as e:
                log(f"Errore rimozione {repo_name}: {traceback.format_exc()}", xbmc.LOGERROR)
                error_count += 1
        progress.close()
        # Aggiorna l'interfaccia
        self.load_data()
        self.populate_list()
        # Mostra riepilogo
        if removed_count > 0 or error_count > 0:
            message = (
                f"Rimozione completata:\n"
                f"[COLOR=lime]{removed_count}[/COLOR] sorgenti rimosse\n"
                f"[COLOR=red]{error_count}[/COLOR] errori"
            )
            if xbmcgui.Dialog().yesno(
                ADDON_NAME, 
                f"{message}\n\nRiavviare Kodi ora per applicare le modifiche?",
                yeslabel="Sì, Riavvia",
                nolabel="No"
            ):
                xbmc.executebuiltin("RestartApp")
            else:
                xbmcgui.Dialog().notification(
                    ADDON_NAME, 
                    "Ricorda di riavviare Kodi per completare la rimozione", 
                    ADDON_ICON, 
                    5000
                )
        else:
            xbmcgui.Dialog().notification(
                ADDON_NAME, 
                "Nessuna sorgente da rimuovere", 
                ADDON_ICON, 
                3000
            )

    def install_single(self, repo, show_dialog=True):
        from resources.lib.kodinerds_downloader import download_latest_kodinerds_zip
        from resources.lib.sandmann_repo_installer import download_sandmann_repo
        from resources.lib.elementum_repo_installer import download_elementum_repo
        
        name = repo.get("name", "").lower()
        added = False
        repo_name = repo.get("name", "Sconosciuto")
        
        if self.is_repo_installed(repo):
            if show_dialog:
                xbmcgui.Dialog().notification(ADDON_NAME, f"La sorgente «{repo_name}» è già presente", ADDON_ICON, 3000)
            return False
        
        try:
            if "kodinerds" in name:
                download_latest_kodinerds_zip()
                added = True
            elif "sandmann" in name:
                download_sandmann_repo()
                added = is_repo_installed_by_id(SANDMANN_REPO_ID)
            elif "elementum" in name:
                added = download_elementum_repo()
            else:
                added = add_source_to_xml(repo)
        except Exception as e:
            log(f"Errore installazione {repo_name}: {traceback.format_exc()}", xbmc.LOGERROR)
            if show_dialog:
                xbmcgui.Dialog().notification(ADDON_NAME, f"Errore installazione {repo_name}", ADDON_ICON, 3000)
            return False
        
        if added:
            self.load_data()
            self.populate_list()
        
        if added and show_dialog:
            if xbmcgui.Dialog().yesno(ADDON_NAME, f"Sorgente «{repo_name}» aggiunta.\nRiavviare ora?", yeslabel="Sì", nolabel="No"):
                xbmc.executebuiltin("RestartApp")
            else:
                xbmcgui.Dialog().notification(ADDON_NAME, "Ricorda di riavviare Kodi.", ADDON_ICON, 3000)
        
        log(f"Installazione {repo_name}: {'successo' if added else 'fallita'}")
        return added

    def uninstall_single(self, repo, show_dialog=True):
        name = repo.get("name", "").lower()
        repo_name = repo.get("name", "Sconosciuto")
        
        if show_dialog:
            if not xbmcgui.Dialog().yesno(
                ADDON_NAME, 
                f"Vuoi davvero rimuovere la sorgente?\n\n[COLOR=red]{repo_name}[/COLOR]",
                yeslabel="Rimuovi",
                nolabel="Annulla"
            ):
                return False
        
        removed = False
        try:
            # Repository normali (non speciali)
            if not ("kodinerds" in name or "sandmann" in name or "elementum" in name):
                removed = remove_source_from_xml(repo)
            # Repository speciali
            else:
                # Determina gli ID da rimuovere
                repo_ids = []
                if "kodinerds" in name:
                    repo_ids.append(KODINERDS_REPO_ID)
                if "sandmann" in name:
                    repo_ids.extend([SANDMANN_REPO_ID, "repository.sandmann79", "repository.sandmann79s"])
                if "elementum" in name:
                    repo_ids.append(ELEMENTUM_REPO_ID)
                
                # Rimuovi tutte le cartelle corrispondenti
                for repo_id in repo_ids:
                    if remove_physical_repo(repo_id):
                        removed = True
        except Exception as e:
            log(f"Errore rimozione fisica {repo_name}: {traceback.format_exc()}", xbmc.LOGERROR)
            if show_dialog:
                xbmcgui.Dialog().notification(ADDON_NAME, f"Errore rimozione {repo_name}", ADDON_ICON, 3000)
            return False
        
        # Se abbiamo rimosso qualcosa, aggiorniamo lo stato
        if removed:
            # Kodi non sarà consapevole della rimozione finché non viene riavviato
            # Quindi forziamo un refresh dell'interfaccia
            self.load_data()
            self.populate_list()
            # Consiglia il riavvio
            if show_dialog:
                if xbmcgui.Dialog().yesno(ADDON_NAME, 
                    f"Sorgente «{repo_name}» rimossa.\n\n"
                    "Nota: Kodi potrebbe non aggiornare la lista degli addon finché non viene riavviato.\n\n"
                    "Riavviare ora?",
                    yeslabel="Sì",
                    nolabel="No"):
                    xbmc.executebuiltin("RestartApp")
                else:
                    xbmcgui.Dialog().notification(ADDON_NAME, "Ricorda di riavviare Kodi.", ADDON_ICON, 3000)
            log(f"Rimozione fisica {repo_name}: successo")
        else:
            if show_dialog:
                xbmcgui.Dialog().notification(ADDON_NAME, "Nessuna cartella da rimuovere", ADDON_ICON, 3000)
            log(f"Rimozione fisica {repo_name}: nessuna cartella trovata")
        return removed

if __name__ == "__main__":
    xbmc.sleep(300)
    win = RepoManagerGUI("RepoManagerGUI.xml", ADDON_PATH, "default")
    win.doModal()
    del win