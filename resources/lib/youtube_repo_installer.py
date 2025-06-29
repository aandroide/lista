# -*- coding: utf-8 -*-
import os
import xml.etree.ElementTree as ET
import requests
import xbmcgui
import xbmcvfs
from resources.lib.utils import log

def get_latest_youtube_zip_url(api_url):
    """
    Prova a ottenere l'URL dello ZIP ufficiale dalla GitHub API releases/latest.
    Se fallisce (404 o nessun asset), usa la GitHub API tags per ricavare il tag più recente
    e restituisce l'URL della pagina di release tag (HTML) da usare come sorgente.
    """
    api_url = api_url.rstrip('/')
    headers = {
        'Accept': 'application/vnd.github.v3+json',
        'User-Agent': 'Kodi-YouTube-Installer'
    }
    # 1) Proviamo la API releases/latest
    try:
        r = requests.get(api_url, headers=headers, timeout=10)
        if r.status_code == 404:
            raise Exception("No releases/latest API")
        r.raise_for_status()
        data = r.json()
        for asset in data.get('assets', []):
            name = asset.get('name', '')
            if name.endswith('.zip') and 'unofficial' not in name.lower():
                return asset.get('browser_download_url')
    except Exception as e:
        log(f"GitHub releases API failed: {e}", xbmc.LOGWARNING)

    # 2) Fallback: GitHub API tags
    try:
        tags_api_url = api_url.replace('/releases/latest', '/tags')
        r2 = requests.get(tags_api_url, headers=headers, timeout=10)
        r2.raise_for_status()
        tags = r2.json()
        if isinstance(tags, list) and tags:
            tag_name = tags[0].get('name')
            if tag_name:
                # Restituisce la pagina HTML del release tag
                return f"https://github.com/anxdpanic/plugin.video.youtube/releases/tag/{tag_name}"
    except Exception as e:
        log(f"GitHub tags API failed: {e}", xbmc.LOGERROR)

    return None


def download_latest_youtube_zip(api_url):
    """
    Aggiunge a sources.xml l'ultima release di YouTube:
    - primo asset zip via releases API
    - oppure la pagina di tag HTML come sorgente
    """
    source_url = get_latest_youtube_zip_url(api_url)
    if not source_url:
        xbmcgui.Dialog().notification(
            "YouTube Installer",
            "Impossibile recuperare la top release di YouTube",
            xbmcgui.NOTIFICATION_ERROR
        )
        return False

    sources_path = xbmcvfs.translatePath("special://profile/sources.xml")
    try:
        if os.path.exists(sources_path):
            tree = ET.parse(sources_path)
            root = tree.getroot()
        else:
            root = ET.Element('sources')
            tree = ET.ElementTree(root)

        files_node = root.find('files') or ET.SubElement(root, 'files')

        # Verifica esistenza
        for source in files_node.findall('source'):
            path_elem = source.find('path')
            if path_elem is not None and path_elem.text == source_url:
                return False

        # Aggiungi entry
        src = ET.SubElement(files_node, 'source')
        ET.SubElement(src, 'name').text = 'YouTube'
        ET.SubElement(src, 'path', pathversion='1').text = source_url
        ET.SubElement(src, 'allowsharing').text = 'true'

        # Indenta per leggibilità
        def indent(elem, level=0):
            spacer = '  '
            prefix = '\n' + level*spacer
            if len(elem):
                if not elem.text or not elem.text.strip():
                    elem.text = prefix + spacer
                for child in elem:
                    indent(child, level+1)
                if not child.tail or not child.tail.strip():
                    child.tail = prefix
            else:
                if level and (not elem.tail or not elem.tail.strip()):
                    elem.tail = prefix
        indent(root)

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
