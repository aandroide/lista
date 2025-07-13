# File: default.py
# -*- coding: utf-8 -*-

import xbmc
import xbmcgui
import xbmcaddon
import xbmcvfs
import os
import shutil
import tempfile
import traceback

from resources.lib.utils import (
    get_sources_list,
    log
)
from resources.lib.youtube_installer import install_youtube_addon
from resources.lib.trakt_installer import install_trakt_addon

from resources.lib.repo_installer import (
    install_repo,
    uninstall_repo,
    install_all_repos,
    uninstall_all_repos,
    is_repo_installed
)
from resources.lib.update_checker import check_for_updates
from resources.lib.first_run import show_intro_message_once
from resources.lib.qr_generator import generate_qr_code
from resources.lib.icon_utils import normalize_folder_name, create_icon_folder_if_missing

ADDON        = xbmcaddon.Addon()
ADDON_ID     = ADDON.getAddonInfo('id')
ADDON_NAME   = ADDON.getAddonInfo('name')
ADDON_ICON   = ADDON.getAddonInfo('icon')
ADDON_PATH   = xbmcvfs.translatePath(ADDON.getAddonInfo('path'))

# Percorsi e settings
LOCAL_JSON      = os.path.join(ADDON_PATH, 'resources', 'addons.json')
GITHUB_USER     = ADDON.getSetting("github_user").strip() or "aandroide"
GITHUB_REPO     = ADDON.getSetting("github_repo").strip() or "lista"
GITHUB_BRANCH   = ADDON.getSetting("github_branch").strip() or "master"
REMOTE_URL      = f"https://raw.githubusercontent.com/{GITHUB_USER}/{GITHUB_REPO}/{GITHUB_BRANCH}/resources/addons.json"
BACKUP_JSON     = os.path.join(ADDON_PATH, 'resources', 'addons_backup.json')
FIRST_RUN_FILE  = os.path.join(ADDON_PATH, '.firstrun')
LAST_ETAG_FILE  = os.path.join(ADDON_PATH, '.last_etag')
NO_TELEGRAM_IMG = os.path.join(ADDON_PATH, 'resources', 'skins', 'default', 'media', 'no-telegram.png')

# Controllo aggiornamenti all'avvio
if check_for_updates(
    ADDON_NAME=ADDON_NAME,
    ADDON_ICON=ADDON_ICON,
    LOCAL_JSON=LOCAL_JSON,
    BACKUP_JSON=BACKUP_JSON,
    LAST_ETAG_FILE=LAST_ETAG_FILE,
    REMOTE_URL=REMOTE_URL
):
    log(f"{ADDON_NAME}: File addons.json aggiornato")
else:
    log(f"{ADDON_NAME}: Nessun aggiornamento disponibile")

# Messaggio introduttivo
show_intro_message_once(ADDON_NAME, FIRST_RUN_FILE)


class RepoManagerGUI(xbmcgui.WindowXML):
    def __init__(self, *args, **kwargs):
        super().__init__()
        self.sources = []
        self.selected_index = 0
        self.controls = {}

    def onInit(self):
        self.controls = {
            'list':         self.getControl(100),
            'title':        self.getControl(101),
            'static_label': self.getControl(102),
            'description':  self.getControl(200),
            'link':         self.getControl(103),
            'qr':           self.getControl(300)
        }
        self.load_data()
        self.populate_list()
        self.setFocusId(100)

    def load_data(self):
        try:
            sources = get_sources_list()
            if ADDON.getSetting("ShowAdult") != "true":
                sources = [s for s in sources if s.get("name") != "Dobbelina repo (Cumination)"]
            self.sources = sources
            log(f"Caricate {len(self.sources)} sorgenti")
        except Exception as e:
            log(f"Errore caricamento dati: {str(e)}", xbmc.LOGERROR)
            log(traceback.format_exc(), xbmc.LOGERROR)

    def populate_list(self):
        lst = self.controls['list']
        lst.reset()
        if not self.sources:
            lst.addItem(xbmcgui.ListItem("Nessun repository disponibile"))
            return

        icons_base = os.path.join(ADDON_PATH, 'resources', 'icone')
        os.makedirs(icons_base, exist_ok=True)
        default_icon = os.path.join(icons_base, 'default.png')

        for repo in self.sources:
            folder = normalize_folder_name(repo['name'])
            folder_path = os.path.join(icons_base, folder)
            create_icon_folder_if_missing(folder_path)

            icon = None
            if os.path.isdir(folder_path):
                for f in os.listdir(folder_path):
                    if f.lower().startswith('icon'):
                        icon = os.path.join(folder_path, f)
                        break
            if not icon and os.path.exists(default_icon):
                icon = default_icon

            item = xbmcgui.ListItem(repo['name'])
            if icon:
                item.setArt({'icon': icon})
            item.setProperty('description', repo.get('description', ''))
            item.setProperty('telegram', repo.get('telegram', ''))
            
            # Gestione speciale per YouTube e Trakt
            if repo.get('name').lower() == 'youtube' or repo.get('name') == 'Trakt Addon':
                item.setProperty('checked', "false")
                item.setProperty('action_label', "Installa")
            else:
                installed = is_repo_installed(repo)
                item.setProperty('checked', "true" if installed else "false")
                item.setProperty('action_label', "Rimuovi" if installed else "Aggiungi")

            lst.addItem(item)

        lst.selectItem(0)
        self.selected_index = 0
        self.update_display()

    def update_display(self):
        if not self.sources or self.selected_index >= len(self.sources):
            return

        repo     = self.sources[self.selected_index]
        name     = repo.get('name', '')
        desc     = repo.get('description', '')
        tg_link  = repo.get('telegram', '')

        self.controls['title'].setLabel(name)
        self.controls['description'].setText(desc)

        if name.lower() == 'youtube repo':
            self.controls['static_label'].setLabel("Istruzioni per la creazione delle chiavi API Youtube")
        else:
            self.controls['static_label'].setLabel("Canale di supporto Telegram")

        self.controls['link'].setLabel(tg_link or "Nessun link disponibile")
        qr_path = generate_qr_code(tg_link, name) if tg_link else NO_TELEGRAM_IMG
        self.controls['qr'].setImage(qr_path)

    def onAction(self, action):
        action_id = action.getId()
        if action_id in (xbmcgui.ACTION_NAV_BACK, xbmcgui.ACTION_PREVIOUS_MENU):
            self.close()
            return

        if self.getFocusId() == 100:
            new_index = self.controls['list'].getSelectedPosition()
            if new_index != self.selected_index and new_index < len(self.sources):
                self.selected_index = new_index
                self.update_display()
                
        # Gestione del tasto Invio
        if action_id == xbmcgui.ACTION_SELECT_ITEM and self.getFocusId() == 100:
            self.handle_repo_click()

    def onClick(self, controlId):
        if controlId == 100:  # Clic sulla lista
            self.handle_repo_click()
        elif controlId == 500:  # Aggiungi Tutti
            self.install_all()
        elif controlId == 700:  # Rimuovi Tutti
            self.uninstall_all()
        elif controlId == 600:  # Aggiorna Lista
            self.refresh_list()
        elif controlId == 202:  # Apri Gestore File
            xbmc.executebuiltin("ActivateWindow(filemanager)")
            
    def handle_repo_click(self):
        """Gestione del click su un elemento della lista"""
        try:
            self.selected_index = self.controls['list'].getSelectedPosition()
            if self.selected_index >= len(self.sources):
                return

            repo = self.sources[self.selected_index]
            name = repo.get('name', '')
            log(f"Click su repository: {name}", xbmc.LOGINFO)
            
            # Gestione speciale per YouTube
            if name.lower() == 'youtube repo':
                options = ["Scarica ultima versione Official", "Scarica ultima versione Beta"]
                choice = xbmcgui.Dialog().select("YouTube Addon repo", options)
                if choice < 0:
                    return
                    
                log(f"Scelta YouTube: {'Beta' if choice == 1 else 'Official'}", xbmc.LOGINFO)
                success = install_youtube_addon(use_beta=(choice == 1))
                
                if success:
                    log("Installazione YouTube completata con successo", xbmc.LOGINFO)
                    if xbmcgui.Dialog().yesno(
                        ADDON_NAME,
                        "File di YouTube scaricato con successo! Per completare l'installazione, dopo il riavvio vai in 'Installa da file zip' -> 'YouTube Install'.\n\nRiavviare Kodi ora?",
                        yeslabel="Sì",
                        nolabel="No"
                    ):
                        xbmc.executebuiltin("RestartApp")
                    else:
                        xbmcgui.Dialog().notification(
                            ADDON_NAME,
                            "Ricorda di riavviare Kodi per vedere il file zip in 'Installa da file zip'",
                            ADDON_ICON,
                            3000
                        )
                else:
                    log("Errore durante l'installazione di YouTube", xbmc.LOGERROR)
                return
            
            # Gestione speciale per Trakt
            if name == 'Trakt Addon repo':
                log("Avvio installazione Trakt", xbmc.LOGINFO)
                install_trakt_addon()
                return
            
            # Gestione standard per altri repository
            if is_repo_installed(repo):
                self.uninstall_single(repo, True)
            else:
                self.install_single(repo, True)
                
        except Exception as e:
            log(f"Errore durante il click sul repository: {str(e)}", xbmc.LOGERROR)
            log(traceback.format_exc(), xbmc.LOGERROR)
            xbmcgui.Dialog().notification(
                ADDON_NAME,
                "Errore durante l'operazione",
                xbmcgui.NOTIFICATION_ERROR,
                3000
            )
            
    def refresh_list(self):
        if check_for_updates(
            ADDON_NAME=ADDON_NAME,
            ADDON_ICON=ADDON_ICON,
            LOCAL_JSON=LOCAL_JSON,
            BACKUP_JSON=BACKUP_JSON,
            LAST_ETAG_FILE=LAST_ETAG_FILE,
            REMOTE_URL=REMOTE_URL
        ):
            self.load_data()
            self.populate_list()
            xbmcgui.Dialog().notification(
                ADDON_NAME,
                "Lista repository aggiornata!",
                ADDON_ICON,
                3000
            )

    def install_all(self):
        def progress_callback(index, total, name):
            if progress_dialog.iscanceled():
                return True
            progress_dialog.update((index * 100) // total, f"Elaborazione: {name}")
            return False

        progress_dialog = xbmcgui.DialogProgress()
        progress_dialog.create(ADDON_NAME, "Installazione in corso...")

        added, skipped = install_all_repos(self.sources, progress_callback=progress_callback)
        progress_dialog.close()
        self.load_data()
        self.populate_list()

        xbmcgui.Dialog().ok(
            ADDON_NAME,
            f"Aggiunta completata:\n[COLOR=lime]{added}[/COLOR] sorgenti nuove\n[COLOR=grey]{skipped}[/COLOR] già presenti"
        )

        if added > 0:
            if xbmcgui.Dialog().yesno(ADDON_NAME, "Riavviare Kodi ora?", yeslabel="Sì", nolabel="No"):
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
            "Vuoi davvero rimuovere TUTTE le sorgenti?\n\nQuesta operazione rimuoverà tutte le sorgenti e i repository installati.",
            yeslabel="Rimuovi Tutto",
            nolabel="Annulla"
        ):
            return

        def progress_callback(index, total, name):
            if progress_dialog.iscanceled():
                return True
            progress_dialog.update((index * 100) // total, f"Rimozione: {name}")
            return False

        progress_dialog = xbmcgui.DialogProgress()
        progress_dialog.create(ADDON_NAME, "Rimozione in corso...")

        removed, errors = uninstall_all_repos(self.sources, progress_callback=progress_callback)
        progress_dialog.close()
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

        if is_repo_installed(repo):
            if show_dialog:
                xbmcgui.Dialog().notification(
                    ADDON_NAME,
                    f"La sorgente «{name}» è già presente",
                    ADDON_ICON,
                    3000
                )
            return False

        success = install_repo(repo)

        if success:
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
        elif show_dialog:
            xbmcgui.Dialog().notification(
                ADDON_NAME,
                f"Errore installazione «{name}»",
                ADDON_ICON,
                3000
            )

        return success
        
    def uninstall_single(self, repo, show_dialog=True):
        name = repo['name']
        
        # Chiedi conferma all'utente
        if show_dialog:
            if not xbmcgui.Dialog().yesno(
                ADDON_NAME,
                f"Vuoi davvero rimuovere la sorgente?\n\n[COLOR=red]{name}[/COLOR]",
                yeslabel="Rimuovi",
                nolabel="Annulla"
            ):
                return False

        # Esegui la rimozione
        success = uninstall_repo(repo)

        if success:
            self.load_data()
            self.populate_list()
            if show_dialog:
                if xbmcgui.Dialog().yesno(
                    ADDON_NAME,
                    f"Sorgente «{name}» rimossa.\n\nRiavviare Kodi ora?",
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
        elif show_dialog:
            xbmcgui.Dialog().notification(
                ADDON_NAME,
                f"Errore rimozione «{name}»",
                ADDON_ICON,
                3000
            )

        return success


if __name__ == "__main__":
    xbmc.sleep(300)
    win = RepoManagerGUI("RepoManagerGUI.xml", ADDON_PATH, "default")
    win.doModal()
    del win
