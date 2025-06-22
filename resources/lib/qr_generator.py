# -*- coding: utf-8 -*-
import os
import pyqrcode
import xbmcvfs
import xbmc
from .utils import log

# Percorso dell'immagine alternativa quando la generazione del QR fallisce
NO_TELEGRAM_IMG = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),  # Torna su di un livello (da lib a resources)
    "skins", "default", "media", "no-telegram.png"
)

def generate_qr_code(url, name="qr"):
    """
    Genera un codice QR a partire da un URL e lo salva in una immagine temporanea
    
    Args:
        url (str): L'URL da codificare nel QR code
        name (str): Nome base del file (senza estensione)
    
    Returns:
        str: Percorso completo del file immagine generato, o percorso dell'immagine 
             alternativa in caso di errore
    """
    try:
        qr = pyqrcode.create(url)
        tmp_path = xbmcvfs.translatePath("special://temp")
        img_path = os.path.join(tmp_path, f"{name}_qr.png")
        
        qr.png(img_path, scale=6)  # scale=6 per una dimensione leggibile
        return img_path
        
    except Exception as e:
        log(f"Errore generazione QR: {str(e)}", xbmc.LOGERROR)
        return NO_TELEGRAM_IMG