# Addon & Repo Installer for Kodi

**`plugin.program.addonrepoinstaller`** è un addon per Kodi che consente di installare e disinstallare repository o addon direttamente dall’interfaccia utente, leggendo le informazioni da un file `addons.json`.

---

## 📌 Funzionalità Principali

### ✅ Installazione Sorgenti o ZIP
- Pulsante **"Aggiungi"** per ogni voce del file `addons.json`:
  - Se è una **sorgente online**, viene aggiunta nel file manager.
  - Se è un **file ZIP**, viene installato come repository/addon.
- Il pulsante **"Aggiungi Tutti"** installa tutte le voci elencate.

### ❌ Disinstallazione
- Se un addon/repo è installato:
  - Il pulsante diventa **"Rimuovi"**.
  - Dopo conferma dell’utente, l’addon viene disinstallato.
  - Se necessario, viene rimossa la cartella associata.
  - Stato aggiornato dinamicamente.

### 👁️ Stato Installazione
- Icona `check.png` accanto agli elementi già installati.
- Stato aggiornato in tempo reale.
- Nessun riavvio richiesto per aggiornare la GUI.

### 💬 Supporto Telegram via QR Code
- Se presente, il link Telegram viene trasformato in **QR code**.
- In assenza del link, viene mostrata un’immagine alternativa con **logo barrato**.

### 🛠️ Personalizzazione
- Impostazioni configurabili da GUI:
  - GitHub Username
  - Repository
  - Branch
- Permette di puntare a una lista remota di addon personalizzata.

---

## 🗂 File `addons.json` – Esempio

```json
{
  "name": "Kodinerds Repo",
  "description": "Addon come DAZN, DMax, Playlist Loader...",
  "url": "https://repo.kodinerds.net/addons/repository.kodinerds/",
  "telegram": "https://t.me/esempio"
}
