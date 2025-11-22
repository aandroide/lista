import sys

# Leggi il file
with open('repo_installer.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Trova e modifica le sezioni necessarie
new_lines = []
for i, line in enumerate(lines):
    new_lines.append(line)
    
    # Aggiungi IAGL_REPO_ID dopo ELEMENTUM_REPO_ID
    if 'ELEMENTUM_REPO_ID = "repository.elementumorg"' in line:
        new_lines.append('IAGL_REPO_ID = "repository.zachmorris"\n')
    
    # Aggiungi il check per IAGL in is_repo_installed
    if 'return xbmc.getCondVisibility(f"System.HasAddon({ELEMENTUM_REPO_ID})") == 1' in line:
        new_lines.append('    if "iagl" in name or "zachmorris" in name or "zach morris" in name:\n')
        new_lines.append('        return xbmc.getCondVisibility(f"System.HasAddon({IAGL_REPO_ID})") == 1\n')
    
    # Aggiungi il caso per IAGL in install_repo
    if 'from resources.lib.elementum_repo_installer import download_elementum_repo' in line:
        new_lines.append('        elif "iagl" in lower or "zachmorris" in lower or "zach morris" in lower:\n')
        new_lines.append('            from resources.lib.iagl_repo_installer import download_iagl_repo\n')
        new_lines.append('            return download_iagl_repo()\n')
    
    # Aggiungi il caso per IAGL in uninstall_repo
    if 'return remove_physical_repo(ELEMENTUM_REPO_ID)' in line and i > 60:  # Nel blocco uninstall
        new_lines.append('        elif "iagl" in lower or "zachmorris" in lower or "zach morris" in lower:\n')
        new_lines.append('            return remove_physical_repo(IAGL_REPO_ID)\n')

# Scrivi il file modificato
with open('repo_installer.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print("File modificato con successo!")
