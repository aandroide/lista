import re
import xml.etree.ElementTree as ET
import zipfile
import os
import xbmc

def log_info(msg, prefix="Repo_Addon_installer"):
    xbmc.log(f"[{prefix}] {msg}", xbmc.LOGINFO)

def log_error(msg, prefix="Repo_Addon_installer"):
    xbmc.log(f"[{prefix}] {msg}", xbmc.LOGERROR)

def parse_addon_xml_version(addon_xml_path):
    """Parsa addon.xml per estrarre la versione"""
    try:
        tree = ET.parse(addon_xml_path)
        root = tree.getroot()
        return root.get('version', '0.0.0')
    except Exception as e:
        log_error(f"Errore parsing addon.xml: {e}")
    return '0.0.0'

def get_version_from_zip(zip_path):
    """Estrae la versione da addon.xml dentro uno ZIP"""
    try:
        with zipfile.ZipFile(zip_path, 'r') as z:
            for name in z.namelist():
                if name.endswith('addon.xml') or name == 'addon.xml':
                    with z.open(name) as f:
                        content = f.read().decode('utf-8')
                        root = ET.fromstring(content)
                        version = root.get('version', '0.0.0')
                        return version
    except Exception as e:
        log_error(f"Errore lettura addon.xml da ZIP {zip_path}: {e}")
    return None

def normalize_version(version_str):
    """Normalizza la stringa di versione per il confronto"""
    return re.sub(r'[^a-z0-9\.]', '', version_str.lower())

def is_version_greater(v1, v2):
    """Confronta versioni con suffissi alfanumerici"""
    try:
        from distutils.version import LooseVersion
        v1_norm = normalize_version(v1)
        v2_norm = normalize_version(v2)
        result = LooseVersion(v1_norm) > LooseVersion(v2_norm)
        log_info(f"is_version_greater({v1}, {v2}): {v1_norm} > {v2_norm} = {result}")
        return result
    except Exception as e:
        log_error(f"Errore confronto versioni {v1} vs {v2}: {e}")
        return v1 > v2

def are_versions_equal(v1, v2):
    """Controlla se due versioni sono identiche"""
    try:
        from distutils.version import LooseVersion
        v1_norm = normalize_version(v1)
        v2_norm = normalize_version(v2)
        result = LooseVersion(v1_norm) == LooseVersion(v2_norm)
        log_info(f"are_versions_equal({v1}, {v2}): {v1_norm} == {v2_norm} = {result}")
        return result
    except Exception as e:
        log_error(f"Errore confronto uguaglianza versioni {v1} vs {v2}: {e}")
        return v1 == v2

def get_release_channel(version_str):
    """Identifica il canale di sviluppo (alpha, beta, stable)"""
    if not version_str:
        return "unknown"
    
    version_lower = version_str.lower()
    if "alpha" in version_lower:
        return "alpha"
    elif "beta" in version_lower:
        return "beta"
    return "stable"
