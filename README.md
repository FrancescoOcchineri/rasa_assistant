# 🤖 TARS Assistant

Un assistente vocale intelligente basato su **Rasa**, che controlla la casa tramite **Home Assistant**, gestisce file, risponde alle domande frequenti e ha una **personalità regolabile** su due assi: ironia e sincerità, come il TARS di *Interstellar*.

![Rasa](https://img.shields.io/badge/Rasa-3.6.10-blue) ![Docker](https://img.shields.io/badge/Docker-Enabled-green) ![Python](https://img.shields.io/badge/Python-3.11-yellow) ![Blazor](https://img.shields.io/badge/Blazor-GUI-purple) ![Home Assistant](https://img.shields.io/badge/Home%20Assistant-API-41BDF5) ![Raspberry Pi](https://img.shields.io/badge/Raspberry%20Pi-5-C51A4A)

---

## 📂 Struttura del progetto

- **`tars_assistant/`** → il progetto Rasa vero e proprio.
  - **`actions/actions.py`** → azioni sul file system e generazione con Ollama.
  - **`actions/ha_actions.py`** → 🆕 azioni collegate a Home Assistant (accensione, spegnimento, stato, temperature).
  - **`actions/personalita.py`** → 🆕 personalità regolabile, frasario per fasce di tono e persistenza dei parametri.
  - **`data/nlu.yml`** → intent, entità, regex e retrieval intent delle FAQ.
  - **`data/rules.yml`** → regole che associano intent ad azioni.
  - **`data/stories.yml`** → storie di dialogo.
  - **`domain.yml`** → intent, entità, slot, risposte (anche condizionali) e azioni.
  - **`config.yml`** → pipeline NLU e policy.
  - **`docker-compose.yml`** → configurazione dei container.
  - **`logs/`** → log di Rasa per debug e monitoraggio.
- **`GuiRasa/`** → GUI Blazor Server con chat e log live, scroll automatico e codifica colori.
- **`RasaScripts/log_sender.py`** → 🆕 inoltra in streaming `rasa.log` verso il servizio di raccolta sulla VPS.

---

## 🏗 Architettura dei container

L'infrastruttura si basa su container distinti, ciascuno con un ruolo specifico, che collaborano tramite la rete interna di Docker.

### 🔹 Rasa

Responsabile della NLU e della gestione dei dialoghi.
Il container monta le cartelle del progetto e i log, così da permettere sviluppo, aggiornamenti e debugging senza ricostruzioni frequenti dell'immagine.

### 🔹 Action Server

Dedicato all'esecuzione delle custom actions.
Monta directory locali per consentire operazioni sui file o l'accesso a risorse esterne necessarie durante l'elaborazione delle azioni. È anche il componente che parla con le API di Home Assistant.

### 🔹 Ollama *(opzionale)*

Modello linguistico locale (`mistral`) usato per le risposte generative.
È ancora definito in `docker-compose.yml` e l'azione `action_generate_with_ollama` resta nel progetto, ma **non è più collegata al fallback**: sul Raspberry Pi la generazione su CPU richiede 10-25 secondi e la pipeline vocale è seriale, quindi l'attesa si sommerebbe a tutto il resto. Per riattivarla basta rimettere l'azione nella regola di fallback in `rules.yml`.

### 🔗 Comunicazione

I container comunicano attraverso la rete interna Docker, consentendo a Rasa di invocare in modo sicuro ed efficiente le funzionalità offerte dall'Action Server.

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

### 🏠 Intents domotica 🆕

| Intent | Descrizione | Emoji |
|--------|------------|-------|
| `accendi_dispositivo` | Accende luci, prese, ventilatori, TV… | 💡 |
| `spegni_dispositivo` | Spegne il dispositivo indicato | 🌙 |
| `stato_dispositivo` | Riferisce lo stato di una qualsiasi entità | 🔎 |
| `chiedi_temperatura` | Legge i sensori di temperatura | 🌡️ |

### 🎚 Intents personalità 🆕

| Intent | Descrizione | Emoji |
|--------|------------|-------|
| `imposta_personalita` | Imposta, alza o abbassa ironia e sincerità | 🎛️ |
| `chiedi_personalita` | Riferisce i parametri correnti | ❓ |
| `reimposta_personalita` | Torna ai valori di fabbrica (90% / 90%) | ♻️ |

### 💬 FAQ (retrieval intent) 🆕

`faq/chi_sei`, `faq/cosa_sai_fare`, `faq/creatore`, `faq/dove_giri`.

Una sola regola in `rules.yml` le serve tutte: il **ResponseSelector** sceglie la risposta giusta in base al sottointent riconosciuto. Aggiungere una FAQ costa due righe in `nlu.yml` e una response nel `domain.yml`, senza toccare le regole.

### 🧩 Entità e slot

- Entità: `disco`, `cartella`, `file`, `destinazione`, `dispositivo` 🆕, `livello` 🆕.
- 🆕 I percorsi file e i livelli percentuali sono estratti con **espressioni regolari** (`RegexEntityExtractor`), più affidabili di DIET su pochi esempi.
- 🆕 Slot di personalità (`ironia_livello`, `ironia_grado`, `sincerita_livello`, `sincerita_alta`) usati per il templating e le varianti condizionali delle risposte.

### 📂 File system (`actions.py`)

| Azione | Funzione |
|--------|----------|
| `ActionMostraContenuto` | Elenca i file di una cartella. Mappa le lettere di unità sui mount del container (`C` → `/mnt/c`, `D` → `/mnt/d`, `R` → `/mnt/r`). |
| `ActionEliminaFile` | Elimina un file se esiste, gestendo gli errori. |
| `ActionSpostaFile` | Sposta un file nella destinazione indicata, verificando percorso e permessi. |
| `ActionGenerateWithOllama` | Inoltra il testo a `http://ollama:11434/api/generate` (modello `mistral`, timeout 120s). Non più collegata al fallback. |

### 🏠 Home Assistant (`ha_actions.py`) 🆕

| Azione | Funzione |
|--------|----------|
| `ActionControllaDispositivo` | Accende o spegne: la direzione si deduce dall'intent riconosciuto, quindi una sola implementazione serve entrambi i casi. Domini supportati: `light`, `switch`, `fan`, `input_boolean`, `media_player`, `climate`, `automation`. |
| `ActionStatoDispositivo` | Riferisce lo stato di una qualsiasi entità (anche sensori e porte), traducendo i valori tecnici in parlato: `on` → "accesa", `not_home` → "fuori". |
| `ActionTemperatura` | Riporta tutte le temperature note o quella di un ambiente specifico, selezionando i sensori per `device_class` e non per nome. |

**🔑 Autenticazione: due strade con ripiego automatico**

1. **Token esplicito** in `/share/rasa/.ha_token` (strada in uso): token di accesso a lunga durata, chiamate dirette a Core sulla porta `8123`.
2. **`SUPERVISOR_TOKEN`** come ripiego, se il file non esiste.

Il token sta in un file e non nelle opzioni dell'add-on deliberatamente: modificare le opzioni comporta ricaricare il manifest, lo store e ricostruire l'add-on, mentre un file in `/share` si aggiorna con uno `scp` e un riavvio.

**🎯 Risoluzione dei nomi**

Gli `entity_id` (`light.lampada_salotto_2`) non sono ciò che una persona dice a voce. Invece di mantenere a mano una tabella che invecchia a ogni dispositivo aggiunto, TARS interroga `/api/states` a ogni richiesta e confronta il nome parlato con i `friendly_name` reali: la sottostringa esatta ha la precedenza, poi si passa alla somiglianza approssimata (`difflib`, soglia `0.55`). **Aggiungi una lampadina in Home Assistant e TARS la conosce subito, senza riaddestrare nulla.**

Gli errori sono distinti per causa — token rifiutato, host irraggiungibile, timeout, 404 — così il messaggio orienta chi lo ascolta invece di costringerlo ai log.

### 🎚 Personalità (`personalita.py`) 🆕

| Azione | Funzione |
|--------|----------|
| `ActionImpostaPersonalita` | Imposta una percentuale (`ironia al 60%`) oppure alza/abbassa a passi di 20, con limite 0-100. |
| `ActionStatoPersonalita` | Riferisce i due valori e la combinazione che ne risulta ("pungente", "diplomatico", …). |
| `ActionReimpostaPersonalita` | Riporta tutto ai valori di fabbrica: ironia 90%, sincerità 90%. |

**I due assi.** Nel film TARS ha due manopole distinte, umorismo e onestà. Sono ortogonali e insieme coprono quattro comportamenti invece di due:

| | sincerità alta | sincerità bassa |
|---|---|---|
| **ironia alta** | pungente: dice tutto, e ride | ciarliero, gira intorno |
| **ironia bassa** | referto asciutto, nudo e crudo | burocratico, evasivo |

**Persistenza.** Gli slot di Rasa vivono nel tracker, cioè nella singola conversazione, e Home Assistant apre una sessione nuova a ogni interazione con Assist: un livello impostato oggi sarebbe dimenticato al turno successivo. Lo stato vive quindi fuori dal tracker, con due fonti:

1. le entità `input_number.tars_ironia` e `input_number.tars_sincerita` di Home Assistant, se esistono — fonte autorevole, perché rende i parametri visibili in dashboard, regolabili con uno slider e utilizzabili nelle automazioni ("dopo le 23, ironia al 10%");
2. un file JSON in `/share/rasa/personalita.json`, come ripiego e come cache — funziona sempre, anche senza aver creato nulla in Home Assistant.

La scrittura va su entrambi, la lettura preferisce Home Assistant.

**Propagazione.** Il valore non è la manopola: è che *tutto* cambi. Le frasi delle azioni Python passano da `frase()`, che sceglie la variante adatta alla fascia corrente (basso / medio / alto); le risposte statiche del `domain.yml` usano invece le varianti condizionali di Rasa sullo slot `ironia_grado`. Aggiungere un tono significa aggiungere una riga al frasario, non toccare la logica.

---

## 💬 Flusso della conversazione

```
[Utente]
│
▼
[Rasa NLU] → Determina intent & entities
│
▼
[RulePolicy / Storie] → Invoca azione o risposta
│
├─→ [Action Server] → File system
├─→ [Action Server] → API Home Assistant → 🏠 dispositivi, stati, temperature
├─→ [ResponseSelector] → FAQ
│
▼
[Risposta all'utente, nel tono corrente di TARS]
▲
│
action_default_fallback se la confidenza è sotto 0.65
```

- 🆕 Il fallback pronuncia `utter_default` (tre varianti scelte a caso, così TARS non ripete la stessa frase) e riavvolge il messaggio dal tracker, chiudendo il turno.
- 🆕 Le storie coprono anche le conversazioni che **non** cominciano con un saluto: nell'uso vocale reale nessuno saluta prima di chiedere qualcosa.
- 🆕 Rimosse le regole su `affirm` e `deny`: non avendo contesto conversazionale, qualunque "sì" in qualunque momento finiva su `utter_happy`, in conflitto con le storie.

---

## 🖥 GUI Blazor e log live

- Pagina **Chat** (`/`): invia messaggi a Rasa e visualizza le risposte in tempo reale.
- Pagina **Log** (`/log`): log di Rasa letti direttamente da `logs/rasa.log` con aggiornamento live (polling ogni 2 secondi) e scroll automatico.
  - Input utente: verde brillante
  - Risposta bot: giallo
  - `ERROR`: rosso · `DEBUG`: grigio-blu
- Layout con sidebar comprimibile per spostarsi fra Chat e Log.

### 📡 `RasaScripts/log_sender.py` 🆕

Segue `rasa.log` in coda (`tail`) e inoltra ogni riga via HTTP POST al servizio di raccolta sulla VPS, così la GUI pubblicata può mostrare i log di un'istanza che gira altrove.

---

## 🔍 Debug & Test

- Testare le azioni direttamente nel container Action Server con Python.
- Verificare connettività dei container (`ping`, `curl` — entrambi installati nell'immagine dell'Action Server).
- 🆕 Verificare che Home Assistant risponda: `curl -H "Authorization: Bearer $TOKEN" http://<host>:8123/api/states`.
- Monitorare risorse e performance (`docker stats`).
- Controllare i log per errori o problemi di permessi.

---

## 🚀 Aggiornamento dei container

- Modifiche ad `actions.py`, `ha_actions.py` o `personalita.py` → riavviare **Action Server**.
- Modifiche a `nlu.yml`, `rules.yml`, `stories.yml`, `domain.yml`, `config.yml` → `rasa train` e riavvio del container Rasa.
- Modifiche al Dockerfile → ricostruire il container.
- Log e GUI aggiornati automaticamente senza riavvio della GUI.
- 🆕 Aggiungere un dispositivo in Home Assistant → **nessun riaddestramento**: i nomi sono risolti a runtime.

---

## 🌐 Integrazione Home Assistant, NGINX e VPS

TARS Assistant è integrato con **Home Assistant** (installato come Home Assistant OS su Raspberry Pi 5), utilizzando il microfono ReSpeaker Lite USB 2-Mic Array per l'input vocale.
Le API di Rasa e l'interfaccia **GuiRasa** sono esposte tramite **NGINX** con SSL su una **VPS Webdock**, mentre sia GuiRasa che Home Assistant sono hostati su un dominio personale per un accesso sicuro e centralizzato.

- **VPS**: ospita i container Docker con Rasa, Action Server, GUI Blazor e log, provider utilizzato: **Webdock**.
- **Home Assistant**: installato come **Home Assistant OS su Raspberry Pi 5**, con il quale TARS interagisce tramite API REST con un custom component.
- **Audio Input**: ReSpeaker Lite - USB 2-Mic Array di SeeedStudio per input vocale.
- **Dominio**: sia **GuiRasa** sia **Home Assistant** sono hostati su un dominio personale.
- **NGINX**: reverse proxy + SSL per esporre in sicurezza le API di Rasa.

### 📦 File usati sul Raspberry

| Percorso | Contenuto |
|---|---|
| `/share/rasa/.ha_token` | token di accesso a lunga durata di Home Assistant |
| `/share/rasa/personalita.json` | ironia e sincerità correnti |
| `input_number.tars_ironia` · `input_number.tars_sincerita` | gli stessi parametri, regolabili da dashboard |

---

## ⚠ Note

- Le azioni sul file system operano direttamente sui dischi dell'host montati nel container: da usare con cautela, soprattutto l'eliminazione dei file. È anche il motivo per cui la soglia di fallback è alta.
- I percorsi dei volumi in `docker-compose.yml` sono quelli della macchina di sviluppo e vanno adattati al proprio ambiente; se si cambiano le lettere di unità va aggiornata anche la `mount_map` in `actions.py`.
- `tests/test_stories.yml` è ancora quello generato da `rasa init` (esempi in inglese, intent `bot_challenge` non presente nel domain).
