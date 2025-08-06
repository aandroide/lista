# -*- coding: utf-8 -*-
import os
import pyqrcode
import xbmcvfs
import xbmc
import xbmcaddon
from .utils import log

# Informazioni Addon
ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo('id')

# Percorso dell'immagine alternativa in caso di errore
NO_TELEGRAM_IMG = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),  # Torna su di un livello (da lib a resources)
    "skins", "default", "media", "no-telegram.png"
)

def generate_qr_code(url, name="qr"):
    """
    Genera un codice QR a partire da un URL e lo salva in una cartella permanente

    Args:
        url (str): L'URL da codificare nel QR code
        name (str): Nome base del file (senza estensione)

    Returns:
        str: Percorso completo del file immagine generato, o immagine fallback in caso di errore
    """
    try:
        # Crea il QR code
        qr = pyqrcode.create(url)

        # Cartella dedicata per QR code (special://profile/addon_data/plugin.id/qr/)
        qr_dir = xbmcvfs.translatePath(f"special://profile/addon_data/{ADDON_ID}/qr/")
        
        # Crea la cartella se non esiste
        if not xbmcvfs.exists(qr_dir):
            xbmcvfs.mkdirs(qr_dir)

        # Percorso immagine da generare
        img_path = os.path.join(qr_dir, f"{name}_qr.png")
        
        # Salva il QR code come immagine PNG
        qr.png(img_path, scale=6)  # scale=6 per dimensioni leggibili

        return img_path

    except Exception as e:
        log(f"Errore generazione QR: {str(e)}", xbmc.LOGERROR)
        return NO_TELEGRAM_IMG
