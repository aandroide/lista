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

from resources.lib.utils import (
    get_sources_list, 
    log, 
    safe_download_file, 
    get_existing_sources, 
    remove_physical_repo,
    remove_source_from_xml 
)

from resources.lib.kodinerds_downloader import download_latest_kodinerds_zip
from resources.lib.sandmann_repo_installer import download_sandmann_repo
from resources.lib.elementum_repo_installer import download_elementum_repo
from resources.lib.repo_installer import install_from_html
from resources.lib.update_checker import check_for_updates
from resources.lib.first_run import show_intro_message_once

# Addon constants
ADDON        = xbmcaddon.Addon()
ADDON_ID     = ADDON.getAddonInfo('id')
ADDON_NAME   = ADDON.getAddonInfo('name')
ADDON_ICON   = ADDON.getAddonInfo('icon')
ADDON_PATH   = xbmcvfs.translatePath(ADDON.getAddonInfo('path'))

# Percorsi e impostazioni JSON
LOCAL_JSON      = os.path.join(ADDON_PATH, 'resources', 'addons.json')
GITHUB_USER     = ADDON.getSetting("github_user").strip() or "aandroide"
GITHUB_REPO     = ADDON.getSetting("github_repo").strip() or "lista"
GITHUB_BRANCH   = ADDON.getSetting("github_branch").strip() or "master"
REMOTE_URL      = f"https://raw.githubusercontent.com/{GITHUB_USER}/{GITHUB_REPO}/{GITHUB_BRANCH}/resources/addons.json"
BACKUP_JSON     = os.path.join(ADDON_PATH, 'resources', 'addons_backup.json')
FIRST_RUN_FILE  = os.path.join(ADDON_PATH, ".firstrun")
LAST_ETAG_FILE  = os.path.join(ADDON_PATH, ".last_etag")
NO_TELEGRAM_IMG = os.path.join(ADDON_PATH, "resources", "skins", "default", "media", "no-telegram.png")

# ID esatti dei repository
KODINERDS_REPO_ID  = "repository.kodinerds"
SANDMANN_REPO_ID   = "repository.sandmann79.plugins"
ELEMENTUM_REPO_ID  = "repository.elementumorg"

# chiamo la funzione aggiornamenti
if check_for_updates(
    ADDON_NAME=ADDON_NAME,
    ADDON_ICON=ADDON_ICON,
    LOCAL_JSON=LOCAL_JSON,
    BACKUP_JSON=BACKUP_JSON,
    LAST_ETAG_FILE=LAST_ETAG_FILE,
    REMOTE_URL=REMOTE_URL
):
    xbmc.log(f"{ADDON_NAME}: File addons.json aggiornato", xbmc.LOGINFO)
else:
    xbmc.log(f"{ADDON_NAME}: Nessun aggiornamento disponibile", xbmc.LOGINFO)

# messaggio alla prima esecuzione dell'addon e solo una volta.    
show_intro_message_once(ADDON_NAME, FIRST_RUN_FILE)

def is_repo_installed_by_id(repo_id):
    return xbmc.getCondVisibility(f"System.HasAddon({repo_id})") == 1

def is_any_sandmann_repo_installed():
    return any(
        is_repo_installed_by_id(r)
        for r in [SANDMANN_REPO_ID, "repository.sandmann79", "repository.sandmann79s"]
    )

def is_elementum_repo_installed():
    return is_repo_installed_by_id(ELEMENTUM_REPO_ID)

def generate_qr_code(url, name="qr"):
    try:
        qr = pyqrcode.create(url)
        tmp = xbmcvfs.translatePath("special://temp")
        path = os.path.join(tmp, f"{name}_qr.png")
        qr.png(path, scale=6)
        return path
    except Exception as e:
        log(f"Errore generazione QR: {e}", xbmc.LOGERROR)
        return NO_TELEGRAM_IMG

def add_source_to_xml(repo):
    sources_path = xbmcvfs.translatePath("special://profile/sources.xml")
    name = repo.get("name","Sconosciuto")
    url  = repo.get("url","")
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

    files = root.find("files") or ET.SubElement(root, "files")

    # Evita duplicati
    for s in files.findall("source"):
        p = s.find("path")
        if p is not None and p.text == url:
            return False

    src = ET.SubElement(files, "source")
    ET.SubElement(src, "name").text = name
    ET.SubElement(src, "path", pathversion="1").text = url
    ET.SubElement(src, "allowsharing").text = "true"

    # Indentazione
    def indent(e, level=0):
        sp = "  "
        nl = "\n" + level*sp
        if len(e):
            if not e.text or not e.text.strip():
                e.text = nl + sp
            for c in e:
                indent(c, level+1)
            if not c.tail or not c.tail.strip():
                c.tail = nl
        else:
            if level and (not e.tail or not e.tail.strip()):
                e.tail = nl

    indent(root)
    try:
        xml = ET.tostring(root, encoding='utf-8', xml_declaration=True)
        with open(sources_path, 'wb') as f:
            f.write(xml)
        return True
    except Exception as e:
        log(f"Errore scrittura sources.xml: {e}", xbmc.LOGERROR)
        return False

class RepoManagerGUI(xbmcgui.WindowXML):
    def __init__(self, *args, **kwargs):
        super().__init__()
        self.sources = []
        self.selected_index = 0
        self.existing_urls = []
        self.controls = {}

    def onInit(self):
        self.controls['list']        = self.getControl(100)
        self.controls['title']       = self.getControl(101)
        self.controls['description'] = self.getControl(200)
        self.controls['link']        = self.getControl(103)
        self.controls['qr']          = self.getControl(300)
        self.load_data()
        self.populate_list()
        self.setFocusId(100)

    def load_data(self):
        sources = get_sources_list()
        if ADDON.getSetting("ShowAdult") != "true":
            sources = [s for s in sources if s.get("name") != "Dobbelina repo (Cumination)"]
        self.sources = sources
        self.existing_urls = get_existing_sources()
        log(f"Caricate {len(sources)} sorgenti")

    def is_repo_installed(self, repo):
        name = repo.get("name","").lower()
        url  = repo.get("url","")
        if "kodinerds" in name:
            return is_repo_installed_by_id(KODINERDS_REPO_ID)
        if "sandmann" in name:
            return is_any_sandmann_repo_installed()
        if "elementum" in name:
            return is_elementum_repo_installed()
        return url in self.existing_urls

    def normalize_folder_name(self, name):
        remove = ["repo","repository","addon","per","l'","di","da","e"]
        reps   = {"themoviebd":"tmdb","helper":"hlp","artic":"art",
                  "netflix":"nx","amazon":"az","vod":"video",
                  "cumination":"cumi","elementum":"elem"}
        for k,v in reps.items():
            name = name.replace(k,v)
        words = [w for w in name.split() if w.lower() not in remove]
        n = "_".join(words)
        n = re.sub(r'[^a-z0-9]','_',n.lower())
        n = re.sub(r'_+','_',n).strip('_')
        if len(n)>25:
            parts = n.split('_')
            n = "".join(p[0] for p in parts) if len(parts)>1 else n[:15]
        return n

    def create_icon_folder_if_missing(self, path):
        if not os.path.exists(path):
            try:
                os.makedirs(path)
                log(f"Cartella icona creata: {path}")
            except Exception as e:
                log(f"Errore creazione icona: {e}", xbmc.LOGERROR)

    def populate_list(self):
        lst = self.controls['list']
        lst.reset()
        if not self.sources:
            lst.addItem(xbmcgui.ListItem("Nessun repository disponibile"))
            return

        icons_base = os.path.join(ADDON_PATH,'resources','icone')
        if not os.path.exists(icons_base):
            os.makedirs(icons_base)

        default_icon = os.path.join(icons_base,'default.png')
        for repo in self.sources:
            folder = os.path.join(icons_base, self.normalize_folder_name(repo['name']))
            self.create_icon_folder_if_missing(folder)
            icon = None
            if os.path.isdir(folder):
                for f in os.listdir(folder):
                    if f.lower().startswith('icon'):
                        icon = os.path.join(folder,f); break
            if not icon and os.path.exists(default_icon):
                icon = default_icon

            item = xbmcgui.ListItem(repo['name'])
            if icon: item.setArt({'icon':icon})
            item.setProperty('description', repo.get('description',''))
            item.setProperty('telegram',    repo.get('telegram',''))
            checked = "true" if self.is_repo_installed(repo) else "false"
            item.setProperty('checked', checked)
            item.setProperty('action_label',
                "Rimuovi" if checked=="true" else "Aggiungi")
            lst.addItem(item)

        lst.selectItem(0)
        self.selected_index = 0
        self.update_display()

    def update_display(self):
        r = self.sources[self.selected_index]
        self.controls['title'].setLabel(r.get('name',''))
        self.controls['description'].setText(r.get('description',''))
        tg = r.get('telegram','')
        self.controls['link'].setLabel(tg or "Nessun canale Telegram disponibile")
        img = generate_qr_code(tg, r['name']) if tg else NO_TELEGRAM_IMG
        self.controls['qr'].setImage(img)

    def onAction(self, action):
        aid = action.getId()
        if aid in (xbmcgui.ACTION_NAV_BACK, xbmcgui.ACTION_PREVIOUS_MENU):
            self.close(); return
        if self.getFocusId()==100:
            idx = self.controls['list'].getSelectedPosition()
            if idx!=self.selected_index:
                self.selected_index = idx
                self.update_display()

    def onClick(self, cid):
        if cid==100:
            repo = self.sources[self.controls['list'].getSelectedPosition()]
            if self.is_repo_installed(repo):
                self.uninstall_single(repo, True)
            else:
                self.install_single(repo, True)
        elif cid==500:
            self.install_all()
        elif cid==700:
            self.uninstall_all()
        elif cid==600:
            self.refresh_list()
        elif cid==202:
            xbmc.executebuiltin("ActivateWindow(filemanager)")
        elif cid==203:
            xbmc.executebuiltin('InstallFromZip()')

    def refresh_list(self):
        if check_for_updates():
            self.load_data()
            self.populate_list()
            xbmcgui.Dialog().notification(ADDON_NAME, "Lista aggiornata!", ADDON_ICON, 3000)

    def install_all(self):
        added = skipped = 0
        dlg = xbmcgui.DialogProgress()
        dlg.create(ADDON_NAME, "Installazione in corso...")
        
        for i, repo in enumerate(self.sources):
            if dlg.iscanceled(): 
                break
            dlg.update((i*100)//len(self.sources), repo['name'])
            if self.is_repo_installed(repo):
                skipped += 1
            else:
                if self.install_single(repo, False):
                    added += 1
                else:
                    skipped += 1
        
        dlg.close()
        self.load_data()
        self.populate_list()
        
        xbmcgui.Dialog().ok(
            ADDON_NAME,
            f"Aggiunta completata:\n[COLOR=lime]{added}[/COLOR] sorgenti nuove\n[COLOR=grey]{skipped}[/COLOR] già presenti"
        )
        
        if added > 0:
            if xbmcgui.Dialog().yesno(
                ADDON_NAME, 
                "Riavviare Kodi ora?", 
                yeslabel="Sì", 
                nolabel="No"
            ):
                xbmc.executebuiltin("RestartApp")
            else:
                xbmcgui.Dialog().notification(
                    ADDON_NAME, 
                    "Riavvio richiesto per applicare le modifiche", 
                    ADDON_ICON, 
                    3000
                )

    def uninstall_all(self):
        if not xbmcgui.Dialog().yesno(
            ADDON_NAME,
            "Vuoi davvero rimuovere TUTTE le sorgenti?\n\n"
            "Questa operazione rimuoverà tutte le sorgenti e i repository installati.",
            yeslabel="Rimuovi Tutto",
            nolabel="Annulla"
        ): 
            return
        
        removed = errors = 0
        dlg = xbmcgui.DialogProgress()
        dlg.create(ADDON_NAME, "Rimozione in corso...")
        
        for i, repo in enumerate(self.sources):
            if dlg.iscanceled(): 
                break
            dlg.update((i*100)//len(self.sources), repo['name'])
            if not self.is_repo_installed(repo): 
                continue
            if self.uninstall_single(repo, False):
                removed += 1
            else:
                errors += 1
        
        dlg.close()
        self.load_data()
        self.populate_list()
        
        if removed > 0 or errors > 0:
            message = (
                f"Rimozione completata:\n"
                f"[COLOR=lime]{removed}[/COLOR] sorgenti rimosse\n"
                f"[COLOR=red]{errors}[/COLOR] errori"
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
        name = repo['name']
        lower = name.lower()
        added = False

        if self.is_repo_installed(repo):
            if show_dialog:
                xbmcgui.Dialog().notification(ADDON_NAME, f"La sorgente «{name}» è già presente", ADDON_ICON, 3000)
            return False

        try:
            if "kodinerds" in lower:
                added = download_latest_kodinerds_zip()
            elif "sandmann" in lower:
                added = download_sandmann_repo()
            elif "elementum" in lower:
                added = download_elementum_repo()
            else:
                added = add_source_to_xml(repo)
        except Exception as e:
            log(f"Errore install {name}: {traceback.format_exc()}", xbmc.LOGERROR)
            if show_dialog:
                xbmcgui.Dialog().notification(ADDON_NAME, f"Errore installazione {name}", ADDON_ICON, 3000)
            return False

        if added:
            self.load_data()
            self.populate_list()
            if show_dialog:
                if xbmcgui.Dialog().yesno(
                    ADDON_NAME, 
                    f"Sorgente «{name}» aggiunta con successo.\n\nRiavviare Kodi ora?",
                    yeslabel="Sì",
                    nolabel="No"
                ):
                    xbmc.executebuiltin("RestartApp")
                else:
                    xbmcgui.Dialog().notification(
                        ADDON_NAME, 
                        "Ricorda di riavviare Kodi per completare l'installazione", 
                        ADDON_ICON, 
                        3000
                    )
        return added

    def uninstall_single(self, repo, show_dialog=True):
        name = repo['name']
        lower = name.lower()
        
        if show_dialog:
            if not xbmcgui.Dialog().yesno(
                ADDON_NAME, 
                f"Vuoi davvero rimuovere la sorgente?\n\n[COLOR=red]«{name}»[/COLOR]",
                yeslabel="Rimuovi",
                nolabel="Annulla"
            ):
                return False

        removed = False
        try:
            if any(k in lower for k in ("kodinerds","sandmann","elementum")):
                # rimuovi folder fisici
                if "kodinerds" in lower:
                    removed |= remove_physical_repo(KODINERDS_REPO_ID)
                if "sandmann" in lower:
                    for rid in (SANDMANN_REPO_ID,"repository.sandmann79","repository.sandmann79s"):
                        removed |= remove_physical_repo(rid)
                if "elementum" in lower:
                    removed |= remove_physical_repo(ELEMENTUM_REPO_ID)
            else:
                removed = remove_source_from_xml(repo)
        except Exception as e:
            log(f"Errore uninstall {name}: {traceback.format_exc()}", xbmc.LOGERROR)
            if show_dialog:
                xbmcgui.Dialog().notification(ADDON_NAME, f"Errore rimozione {name}", ADDON_ICON, 3000)
            return False

        if removed:
            self.load_data()
            self.populate_list()
            if show_dialog:
                if xbmcgui.Dialog().yesno(
                    ADDON_NAME,
                    f"Sorgente «{name}» rimossa con successo.\n\nRiavviare Kodi ora?",
                    yeslabel="Sì",
                    nolabel="No"
                ):
                    xbmc.executebuiltin("RestartApp")
                else:
                    xbmcgui.Dialog().notification(
                        ADDON_NAME,
                        "Ricorda di riavviare Kodi per completare la rimozione",
                        ADDON_ICON,
                        3000
                    )
        return removed

if __name__ == "__main__":
    xbmc.sleep(300)
    win = RepoManagerGUI("RepoManagerGUI.xml", ADDON_PATH, "default")
    win.doModal()
    del win