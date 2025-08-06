# -*- coding: utf-8 -*-
import os
import xbmcgui
import xbmc
from .utils import log

def show_intro_message_once(addon_name, first_run_file):
    """
    Mostra un messaggio introduttivo solo al primo avvio
    Args:
        addon_name (str): Nome dell'addon
        first_run_file (str): Percorso del file che segna il primo avvio
    """
    try:
        if not os.path.exists(first_run_file):
            with open(first_run_file, 'w') as f:
                f.write("shown")
            xbmcgui.Dialog().ok(
                addon_name,
                "Prima di procedere ti consigliamo di unirti ai canali Telegram ufficiali.\n"
                "Questo addon non sostituisce le guide ufficiali. Alcuni addon potrebbero necessitare dipendenze aggiuntive."
            )
    except Exception as e:
        log(f"Errore nel messaggio introduttivo: {e}", xbmc.LOGERROR)