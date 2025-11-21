# 🤖 TARS Assistant

Un assistente vocale intelligente basato su **Rasa**, con gestione di file, conversazioni di base e fallback per input non riconosciuti.  

![Rasa](https://img.shields.io/badge/Rasa-3.6.10-blue) ![Docker](https://img.shields.io/badge/Docker-Enabled-green) ![Python](https://img.shields.io/badge/Python-3.11-yellow) ![Blazor](https://img.shields.io/badge/Blazor-GUI-purple)

---

## 📂 Struttura del progetto

- **`actions/`** → Contiene `actions.py` con tutte le azioni personalizzate.  
- **`logs/`** → Log di Rasa per debug e monitoraggio.  
- **`nlu.yml`** → Definizione di **intents** e **entities** per il NLU.  
- **`rules.yml`** → Regole per associare intent ad azioni.  
- **`domain.yml`** → Slot, utterances, intents e risposte predefinite.  
- **`docker-compose.yml`** → Configurazione dei container Docker.  
- **`GuiRasa/`** → Blazor Server GUI con log live, scroll automatico e codifica colori.

---

## 🏗 Architettura dei container

┌─────────────┐ ┌─────────────────┐  
│ RASA │ <---> │ Action Server │  
│ NLU+Dialog │ │ Custom Actions │  
└─────────────┘ └─────────────────┘  

- **Rasa**: gestisce NLU e dialoghi, monta cartelle progetto e log.  
- **Action Server**: esegue le custom actions, monta cartelle locali per operazioni sui file.  
- I container comunicano tramite rete interna Docker.  

---

## ⚙ Configurazione Rasa

### 💡 Intents principali

| Intent | Descrizione | Emoji |
|--------|------------|-------|
| `greet` | Saluti iniziali | 👋 |
| `goodbye` | Addio / chiusura conversazione | 👋💨 |
| `affirm` | Conferma | ✅ |
| `deny` | Negazione | ❌ |
| `mood_great` | Umore positivo | 😄 |
| `mood_unhappy` | Umore negativo | 😞 |

### 📁 Intents gestione file

| Intent | Descrizione | Emoji |
|--------|------------|-------|
| `mostra_contenuto` | Mostra contenuto cartella | 📂 |
| `elimina_file` | Elimina un file | 🗑️ |
| `sposta_file` | Sposta un file in un'altra cartella | 📦 |

---

## 🛠 Custom Actions

### 1️⃣ Mostra contenuto cartella
- Azione: `ActionMostraContenuto`  
- Funzione: mostra i file presenti nella cartella richiesta dall’utente.  
- Input: disco e percorso della cartella.  
- Output: lista dei file presenti.  

### 2️⃣ Elimina file
- Azione: `ActionEliminaFile`  
- Funzione: elimina un file se esiste, gestendo errori.  
- Input: percorso completo del file.  
- Output: conferma eliminazione o errore.  

### 3️⃣ Sposta file
- Azione: `ActionSpostaFile`  
- Funzione: sposta un file nella destinazione specificata, verifica percorso e permessi.  
- Input: file e cartella di destinazione.  
- Output: conferma spostamento o errore.  

---

## 💬 Flusso della conversazione

[Utente]  
│  
▼  
[Rasa NLU] → Determina intent & entities  
│  
▼  
[RulePolicy] → Invoca azione appropriata  
│  
▼  
[Action Server] → Risposta all'utente  
▲  
│  
Fallback se intent non riconosciuto

- Include fallback per input non riconosciuti.  
- Gestisce conversazioni base stile TARS (saluti, addii, umore, conferme/negazioni).  

---

## 🖥 GUI Blazor e log live

- Invia messaggi a Rasa e visualizza risposte in tempo reale.  
- Log Rasa aggiornati nella GUI:
  - Input utente: verde brillante  
  - Risposta bot: giallo  
- Log direttamente letti da `logs/rasa.log` con aggiornamento live  

---

## 🔍 Debug & Test

- Testare le azioni direttamente nel container Action Server con Python.  
- Verificare connettività dei container (`ping`).  
- Monitorare risorse e performance (`docker stats`).  
- Controllare i log per errori o problemi di permessi.  

---

## 🚀 Aggiornamento dei container

- Modifiche ad `actions.py` → riavviare **Action Server**.  
- Modifiche Dockerfile → ricostruire il container.  
- Log e GUI aggiornati automaticamente senza riavvio della GUI.  

---

## 🌐 Integrazione Home Assistant, NGINX e VPS

TARS Assistant può essere integrato con **Home Assistant** (installato come Home Assistant OS su Raspberry Pi 5), utilizzando il microfono ReSpeaker Lite USB 2-Mic Array per input vocale.  
Le API di Rasa e l’interfaccia **GuiRasa** sono esposte tramite **NGINX** con SSL su una **VPS Webdock**, mentre sia GuiRasa che Home Assistant sono hostati su un dominio personale per un accesso sicuro e centralizzato.

- **VPS**: ospita i container Docker con Rasa, Action Server, GUI Blazor e log, provider utilizzato: **Webdock**.  
- **Home Assistant**: installato come **Home Assistant OS su Raspberry Pi 5**, con il quale interagisce TARS tramite API REST con un custom component.  
- **Audio Input**: ReSpeaker Lite - USB 2-Mic Array di SeeedStudio per input vocale.  
- **Dominio**: sia **GuiRasa** sia **Home Assistant** sono hostati su un dominio personale.  
- **NGINX**: reverse proxy + SSL per esporre in sicurezza le API di Rasa.  
