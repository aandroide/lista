# -*- coding: utf-8 -*-
import os
import xml.etree.ElementTree as ET
import requests
import xbmcgui
import xbmcvfs
from resources.lib.utils import log

def get_latest_youtube_zip_url(api_url):
    """
    Interroga l'API GitHub (endpoint passato) per ottenere l'URL diretto dello ZIP ufficiale.
    """
    try:
        r = requests.get(api_url, timeout=10)
        r.raise_for_status()
        data = r.json()
        for asset in data.get('assets', []):
            name = asset.get('name', '')
            if name.endswith('.zip'):
                return asset.get('browser_download_url')
    except Exception as e:
        log(f"Errore recupero ZIP YouTube: {e}", xbmc.LOGERROR)
    return None

def download_latest_youtube_zip(api_url):
    """
    Scarica l'ultima release di YouTube (usando api_url da addons.json)
    e la aggiunge a sources.xml di Kodi.
    """
    zip_url = get_latest_youtube_zip_url(api_url)
    if not zip_url:
        xbmcgui.Dialog().notification(
            "YouTube Installer",
            "Impossibile recuperare l'ultima release di YouTube",
            xbmcgui.NOTIFICATION_ERROR
        )
        return False

    # Path del file sources.xml di Kodi
    sources_path = xbmcvfs.translatePath("special://profile/sources.xml")
    try:
        # Carica o crea l'albero XML
        if os.path.exists(sources_path):
            tree = ET.parse(sources_path)
            root = tree.getroot()
        else:
            root = ET.Element('sources')
            tree = ET.ElementTree(root)

        files_node = root.find('files') or ET.SubElement(root, 'files')

        # Controllo se già presente
        for source in files_node.findall('source'):
            path_elem = source.find('path')
            if path_elem is not None and path_elem.text == zip_url:
                return False  # già configurato

        # Aggiungi nuova entry
        src = ET.SubElement(files_node, 'source')
        ET.SubElement(src, 'name').text = 'YouTube'
        ET.SubElement(src, 'path', pathversion='1').text = zip_url
        ET.SubElement(src, 'allowsharing').text = 'true'

        # Indentazione per leggibilità
        def indent(elem, level=0):
            spacer = '  '
            prefix = '\n' + level * spacer
            if len(elem):
                if not elem.text or not elem.text.strip():
                    elem.text = prefix + spacer
                for child in elem:
                    indent(child, level + 1)
                if not child.tail or not child.tail.strip():
                    child.tail = prefix
            else:
                if level and (not elem.tail or not elem.tail.strip()):
                    elem.tail = prefix

        indent(root)

        # Salva XML
        xml_str = ET.tostring(root, encoding='utf-8', xml_declaration=True)
        with open(sources_path, 'wb') as f:
            f.write(xml_str)

        return True

    except Exception as e:
        log(f"Errore scrittura sources.xml YouTube: {e}", xbmc.LOGERROR)
        xbmcgui.Dialog().notification(
            "YouTube Installer",
            "Errore durante l'inserimento della sorgente YouTube",
            xbmcgui.NOTIFICATION_ERROR
        )
        return False
