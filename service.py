import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs
import os
from resources.lib import github_sync, install_manager

ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo('id')
ADDON_NAME = ADDON.getAddonInfo('name')
ICON_PATH = xbmcvfs.translatePath(
    os.path.join('special://home/addons', ADDON_ID, 'icon.png')
)

def log_info(msg):
    xbmc.log(f"[{ADDON_ID}] {msg}", xbmc.LOGINFO)

def main():
    """Controllo aggiornamenti solo all'avvio"""
    # Controlla aggiornamenti all'avvio
    last_commit = github_sync.read_last_commit()
    remote_commit = github_sync.get_remote_commit()
    
    if remote_commit and remote_commit != last_commit:
        log_info(f"Trovato nuovo commit: {remote_commit[:7]}")
        
        remote_files = github_sync.get_remote_file_list()
        if remote_files:
            github_sync.sync_all(remote_files)
            github_sync.write_last_commit(remote_commit)
            
            # Notifica utente
            xbmcgui.Dialog().notification(
                ADDON_NAME,
                f"Aggiornato al commit {remote_commit[:7]}",
                ICON_PATH,
                3000
            )
    
    # Esegue pulizia all'avvio
    install_manager.cleanup_temp_install_folders()

if __name__ == "__main__":
    main()
