# lista

# Addon & Repo Installer – Kodi Addon Wiki

## 🧩 Addon: `plugin.program.addonrepoinstaller`

### 📌 Scopo
Questo addon per Kodi permette di:
- Visualizzare un elenco di repository e addon personalizzati definiti in un file `addons.json`
- Aggiungerli come sorgenti nel `sources.xml` di Kodi
- Mostrare descrizione, pulsanti di installazione e codice QR per ciascun addon
- Automatizzare il processo di aggiunta senza dover navigare manualmente nel file manager

---

### 🔧 Funzionalità principali

| Funzione | Descrizione |
|---------|-------------|
| 🔍 **Lettura da GitHub** | Carica dinamicamente il file `addons.json` da un repository GitHub configurabile nei settings dell’addon |
| 📂 **Fallback locale** | Se il file remoto non è disponibile, usa `resources/addons.json` come copia locale |
| 🧩 **Parsing `sources.xml`** | Legge le sorgenti già esistenti per evitare duplicati |
| ➕ **Aggiunta repository** | Aggiunge automaticamente una sorgente nel file `sources.xml` se non è già presente |
| 🖼️ **GUI custom** | Interfaccia visuale tramite file `RepoManagerGUI.xml` (colonna sinistra elenco, destra descrizione e QR) |
| 📱 **QR Code** | Genera e visualizza dinamicamente QR code con link al canale Telegram di supporto |
| 🔘 **Pulsanti di azione** | Ogni repo ha un pulsante “Aggiungi” e un pulsante globale “Aggiungi Tutti” |
| ✅ **Check installazione** | Mostra un'icona `check.png` accanto ai repository già aggiunti |

---

### 📦 File e componenti principali

| File | Ruolo |
|------|-------|
| `default.py` | Script principale: gestisce logica, parsing JSON, modifica `sources.xml`, dialoghi QR e GUI |
| `addons.json` | File JSON con lista delle sorgenti: `name`, `description`, `url`, `telegram` |
| `RepoManagerGUI.xml` | Interfaccia visuale personalizzata in stile Kodi |
| `settings.xml` | Permette di modificare user/repo/branch GitHub da cui scaricare `addons.json` |
| `kodinerds_downloader.py` / `sandmann_repo_installer.py` | Script specializzati per l'aggiunta automatica di repo ZIP specifici |
| `media/` | Contiene le immagini per pulsanti, sfondi, icone e QR code |

---

### 📁 Struttura `addons.json` (esempio)

```json
{
  "sources": [
    {
      "name": "The Crew Repo",
      "description": "Repository per addon streaming",
      "url": "https://team-crew.github.io/",
      "telegram": "https://t.me/joinchat/crew_channel"
    },
    {
      "name": "S4Me Repo",
      "description": "Contiene l'addon Stream4Me",
      "url": "https://stream4me.github.io/repo/",
      "telegram": "https://t.me/stream4me_addon"
    }
  ]
}
