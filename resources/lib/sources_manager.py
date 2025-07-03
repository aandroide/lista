# -*- coding: utf-8 -*-
import xml.etree.ElementTree as ET
import xbmcvfs
import os
import xbmc

# Struttura predefinita completa di Kodi
DEFAULT_SOURCES_STRUCTURE = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<sources>
    <programs>
        <default pathversion="1"></default>
    </programs>
    <video>
        <default pathversion="1"></default>
    </video>
    <music>
        <default pathversion="1"></default>
    </music>
    <pictures>
        <default pathversion="1"></default>
    </pictures>
    <files>
        <default pathversion="1"></default>
    </files>
</sources>"""

def create_sources_file_if_missing(sources_path):
    """Crea un nuovo file sources.xml con struttura completa se non esiste"""
    if not os.path.exists(sources_path):
        try:
            with open(sources_path, 'w', encoding='utf-8') as f:
                f.write(DEFAULT_SOURCES_STRUCTURE)
            xbmc.log(f"Creato nuovo file sources.xml: {sources_path}", xbmc.LOGINFO)
            return True
        except Exception as e:
            xbmc.log(f"Errore creazione sources.xml: {str(e)}", xbmc.LOGERROR)
    return False

def get_xml_tree(sources_path):
    """Ottiene l'albero XML, crea il file se mancante o corrotto"""
    create_sources_file_if_missing(sources_path)
    
    try:
        return ET.parse(sources_path)
    except Exception as e:
        xbmc.log(f"Errore parsing sources.xml, ricreo il file: {str(e)}", xbmc.LOGERROR)
        try:
            with open(sources_path, 'w', encoding='utf-8') as f:
                f.write(DEFAULT_SOURCES_STRUCTURE)
            return ET.parse(sources_path)
        except Exception as e2:
            xbmc.log(f"Errore grave ricreazione sources.xml: {str(e2)}", xbmc.LOGERROR)
            return None

def indent_xml(elem, level=0):
    """Funzione ricorsiva per indentare correttamente l'XML"""
    spacer = "  "  # 2 spazi per livello
    indent_prefix = "\n" + level * spacer
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = indent_prefix + spacer
        if not elem.tail or not elem.tail.strip():
            elem.tail = indent_prefix
        for i, child in enumerate(elem):
            indent_xml(child, level + 1)
            if i == len(elem) - 1:  # Ultimo figlio
                child.tail = indent_prefix
            else:
                child.tail = indent_prefix + spacer
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = indent_prefix

def save_xml(root, sources_path):
    """Salva l'XML formattato correttamente"""
    try:
        # Formatta l'XML
        indent_xml(root)
        
        # Genera stringa XML
        xml_str = ET.tostring(root, encoding='utf-8', method='xml')
        
        # Aggiungi dichiarazione XML
        xml_declaration = b'<?xml version="1.0" encoding="utf-8" standalone="yes"?>\n'
        xml_str = xml_declaration + xml_str
        
        # Salva il file
        with open(sources_path, 'wb') as f:
            f.write(xml_str)
        return True
    except Exception as e:
        xbmc.log(f"Errore scrittura sources.xml: {str(e)}", xbmc.LOGERROR)
        return False

def add_source_to_xml(repo):
    """Aggiunge una sorgente al file sources.xml"""
    sources_path = xbmcvfs.translatePath("special://profile/sources.xml")
    name = repo.get("name", "Sconosciuto")
    url = repo.get("url", "")
    
    if not url:
        xbmc.log(f"Sorgente '{name}' senza URL", xbmc.LOGWARNING)
        return False

    tree = get_xml_tree(sources_path)
    if not tree:
        return False
        
    root = tree.getroot()
    files_node = root.find("files")
    if files_node is None:
        files_node = ET.SubElement(root, "files")

    # Controlla se la sorgente esiste già
    for source in files_node.findall("source"):
        path_elem = source.find('path')
        if path_elem is not None and path_elem.text == url:
            return False  # Sorgente già presente

    # Aggiungi la nuova sorgente
    source = ET.SubElement(files_node, "source")
    ET.SubElement(source, "name").text = name
    ET.SubElement(source, "path", pathversion="1").text = url
    ET.SubElement(source, "allowsharing").text = "true"

    return save_xml(root, sources_path)

def remove_source_from_xml(repo):
    """Rimuove una sorgente dal file sources.xml"""
    sources_path = xbmcvfs.translatePath("special://profile/sources.xml")
    url = repo.get("url", "")
    
    if not os.path.exists(sources_path) or not url:
        return False

    tree = get_xml_tree(sources_path)
    if not tree:
        return False
        
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
        return save_xml(root, sources_path)
    return False