
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
```

---

## 🖼️ Interfaccia Grafica
- GUI personalizzata fullscreen (`RepoManagerGUI.xml`)
- Colonna sinistra: lista addon
- Colonna destra: descrizione, QR, pulsanti

---

## 📁 Struttura
- `default.py`: logica principale
- `resources/addons.json`: sorgente dati
- `resources/lib/`: moduli per installazione ZIP e sorgenti
- `resources/skins/default/`: media, GUI XML e immagini

---

## 🔄 Compatibilità
- Kodi 20+ (testato su Android e Windows)
- Nessuna modifica diretta a `sources.xml`
- Supporta aggiornamento dinamico senza riavvio

---

## 📖 Licenza
Questo addon è fornito a scopo dimostrativo ed educativo. Non sostituisce guide ufficiali. Alcuni addon potrebbero necessitare di dipendenze esterne.



---

## 🔥 Utenti Fire TV Stick: Addon indispensabile!

Se usi **Kodi su Fire TV Stick**, probabilmente conosci questa procedura noiosa:

> *Apri il gestore file → Aggiungi sorgente → Scrivi l’URL manualmente → Ripeti per ogni addon...*

😩 È scomodo, lento e frustrante.

Con **Addon & Repo Installer**:
- Niente più digitazione manuale!
- Clicca su **"Aggiungi"** per installare la sorgente o il file ZIP.
- Clicca su **"Aggiungi Tutti"** per installarli tutti in un colpo.
- Stato visivo in tempo reale (icona ✅ per installati).
- **Stesso pulsante = anche disinstallazione** (diventa "Rimuovi").

### 📲 Telegram incluso
- Ogni repo può includere un link Telegram.
- Viene generato **QR Code** scansionabile.
- In mancanza, viene mostrato un logo "no Telegram" barrato.

### 🎮 Facile da usare anche col telecomando
- Navigazione ottimizzata per Fire TV.
- GUI a schermo intero, leggibile e chiara.
- Nessun bisogno di tastiere o digitazioni complesse.

**Risparmia tempo. Evita errori. Installa tutto con pochi clic.**

---
