# -*- coding: utf-8 -*-
import xml.dom.minidom as minidom
import xbmcvfs
import os
import xbmc
import re

def ensure_media_sections(doc):
    """Garantisce che tutte le sezioni media siano presenti nel documento"""
    root = doc.documentElement
    required_sections = ['programs', 'video', 'music', 'pictures', 'files']
    
    for section in required_sections:
        # Controlla se la sezione esiste
        sections = root.getElementsByTagName(section)
        if not sections:
            # Crea la sezione mancante
            section_node = doc.createElement(section)
            default_node = doc.createElement("default")
            default_node.setAttribute("pathversion", "1")
            section_node.appendChild(default_node)
            root.appendChild(section_node)

def create_sources_file_if_missing(sources_path):
    """Crea un nuovo file sources.xml con struttura completa se non esiste"""
    if not os.path.exists(sources_path):
        try:
            xmldoc = minidom.Document()
            sources_node = xmldoc.createElement("sources")
            xmldoc.appendChild(sources_node)
            
            # Crea tutte le sezioni necessarie
            for media_type in ['programs', 'video', 'music', 'pictures', 'files']:
                type_node = xmldoc.createElement(media_type)
                default_node = xmldoc.createElement("default")
                default_node.setAttribute("pathversion", "1")
                type_node.appendChild(default_node)
                sources_node.appendChild(type_node)
            
            # Salva il nuovo file
            with open(sources_path, 'wb') as f:
                pretty_xml = xmldoc.toprettyxml(indent="  ", encoding="utf-8")
                cleaned_xml = b'\n'.join([line for line in pretty_xml.splitlines() if line.strip()])
                f.write(cleaned_xml)
            
            xbmc.log(f"Creato nuovo file sources.xml: {sources_path}", xbmc.LOGINFO)
            return True
        except Exception as e:
            xbmc.log(f"Errore creazione sources.xml: {str(e)}", xbmc.LOGERROR)
    return False

def get_xml_document(sources_path):
    """Ottiene il documento XML, crea il file se mancante o corrotto"""
    create_sources_file_if_missing(sources_path)
    
    try:
        doc = minidom.parse(sources_path)
        ensure_media_sections(doc)
        return doc
    except Exception as e:
        xbmc.log(f"Errore parsing sources.xml, ricreo il file: {str(e)}", xbmc.LOGERROR)
        try:
            # Ricrea completamente il file XML
            xmldoc = minidom.Document()
            sources_node = xmldoc.createElement("sources")
            xmldoc.appendChild(sources_node)
            
            for media_type in ['programs', 'video', 'music', 'pictures', 'files']:
                type_node = xmldoc.createElement(media_type)
                default_node = xmldoc.createElement("default")
                default_node.setAttribute("pathversion", "1")
                type_node.appendChild(default_node)
                sources_node.appendChild(type_node)
            
            # Salva il nuovo file
            with open(sources_path, 'wb') as f:
                pretty_xml = xmldoc.toprettyxml(indent="  ", encoding="utf-8")
                cleaned_xml = b'\n'.join([line for line in pretty_xml.splitlines() if line.strip()])
                f.write(cleaned_xml)
            
            return minidom.parse(sources_path)
        except Exception as e2:
            xbmc.log(f"Errore grave ricreazione sources.xml: {str(e2)}", xbmc.LOGERROR)
            return None

def save_xml(doc, sources_path):
    """Salva l'XML formattato correttamente"""
    try:
        # Genera XML formattato e pulito
        pretty_xml = doc.toprettyxml(indent="  ", encoding="utf-8")
        cleaned_xml = b'\n'.join([line for line in pretty_xml.splitlines() if line.strip()])
        
        # Salva il file
        with open(sources_path, 'wb') as f:
            f.write(cleaned_xml)
        return True
    except Exception as e:
        xbmc.log(f"Errore scrittura sources.xml: {str(e)}", xbmc.LOGERROR)
        return False

def add_source_to_xml(repo):
    """Aggiunge una sorgente al file sources.xml nella sezione files"""
    sources_path = xbmcvfs.translatePath("special://profile/sources.xml")
    name = repo.get("name", "Sconosciuto")
    url = repo.get("url", "")
    
    if not url:
        xbmc.log(f"Sorgente '{name}' senza URL", xbmc.LOGWARNING)
        return False

    doc = get_xml_document(sources_path)
    if not doc:
        return False
        
    # Garantisce che tutte le sezioni siano presenti
    ensure_media_sections(doc)
    
    root = doc.documentElement
    
    # Trova la sezione files
    files_nodes = root.getElementsByTagName("files")
    if not files_nodes:
        # Crea la sezione files se mancante
        files_node = doc.createElement("files")
        default_node = doc.createElement("default")
        default_node.setAttribute("pathversion", "1")
        files_node.appendChild(default_node)
        root.appendChild(files_node)
    else:
        files_node = files_nodes[0]

    # Controlla se la sorgente esiste già
    for source in files_node.getElementsByTagName("source"):
        path_elems = source.getElementsByTagName("path")
        if path_elems and path_elems[0].firstChild and path_elems[0].firstChild.data == url:
            return False  # Sorgente già presente

    # Crea la nuova sorgente
    source_elem = doc.createElement("source")
    
    # Elemento name
    name_elem = doc.createElement("name")
    name_elem.appendChild(doc.createTextNode(name))
    source_elem.appendChild(name_elem)
    
    # Elemento path
    path_elem = doc.createElement("path")
    path_elem.setAttribute("pathversion", "1")
    path_elem.appendChild(doc.createTextNode(url))
    source_elem.appendChild(path_elem)
    
    # Elemento allowsharing
    allowsharing_elem = doc.createElement("allowsharing")
    allowsharing_elem.appendChild(doc.createTextNode("true"))
    source_elem.appendChild(allowsharing_elem)
    
    # Aggiungi la sorgente alla sezione files
    files_node.appendChild(source_elem)

    return save_xml(doc, sources_path)

def remove_source_from_xml(repo):
    """Rimuove una sorgente dal file sources.xml"""
    sources_path = xbmcvfs.translatePath("special://profile/sources.xml")
    url = repo.get("url", "")
    
    if not os.path.exists(sources_path) or not url:
        return False

    doc = get_xml_document(sources_path)
    if not doc:
        return False
        
    # Garantisce che tutte le sezioni siano presenti
    ensure_media_sections(doc)
    
    root = doc.documentElement
    files_nodes = root.getElementsByTagName("files")
    if not files_nodes:
        return False
        
    files_node = files_nodes[0]
    removed = False

    # Trova tutte le sorgenti
    sources = files_node.getElementsByTagName("source")
    for source in sources:
        path_elems = source.getElementsByTagName("path")
        if path_elems and path_elems[0].firstChild and path_elems[0].firstChild.data == url:
            files_node.removeChild(source)
            removed = True
            break

    if removed:
        return save_xml(doc, sources_path)
    return False
