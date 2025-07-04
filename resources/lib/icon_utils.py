# -*- coding: utf-8 -*-
import os
import re
import xbmc
from resources.lib.utils import log

def normalize_folder_name(name):
    remove = ["repo", "repository", "addon", "per", "l'", "di", "da", "e"]
    reps = {
        "themoviebd": "tmdb", "helper": "hlp", "artic": "art",
        "netflix": "nx", "amazon": "az", "vod": "video",
        "cumination": "cumi", "elementum": "elem"
    }
    
    # Sostituzioni
    for k, v in reps.items():
        name = name.replace(k, v)
    
    # Rimozione parole chiave e normalizzazione
    words = [w for w in name.split() if w.lower() not in remove]
    normalized = "_".join(words)
    normalized = re.sub(r'[^a-z0-9]', '_', normalized.lower())
    normalized = re.sub(r'_+', '_', normalized).strip('_')
    
    # Accorciamento se necessario
    if len(normalized) > 25:
        parts = normalized.split('_')
        normalized = "".join(p[0] for p in parts) if len(parts) > 1 else normalized[:15]
    
    return normalized

def create_icon_folder_if_missing(path):
    if not os.path.exists(path):
        try:
            os.makedirs(path)
            log(f"Cartella icona creata: {path}")
            return True
        except Exception as e:
            log(f"Errore creazione cartella: {str(e)}", xbmc.LOGERROR)
            return False
    return True