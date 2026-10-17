import requests
import time
import os

# -----------------------------
# Configurazione
# -----------------------------
# URL del server Flask sulla VPS
URL = "http://92.113.148.110:5002/receive-logs"

# Percorso completo del file di log di Rasa sul PC
LOG_PATH = "R:/Utente/rasa/tars_assistant/logs/rasa.log" 

# Intervallo di polling in secondi
SLEEP_INTERVAL = 0.5

# -----------------------------
# Controllo che il file esista
# -----------------------------
if not os.path.exists(LOG_PATH):
    print(f"Errore: il file di log non esiste: {LOG_PATH}")
    exit(1)

# -----------------------------
# Funzione principale
# -----------------------------
with open(LOG_PATH, "r", encoding="utf-8") as f:
    f.seek(0, 2)  # Vai alla fine del file
    print(f"Inizio invio log a {URL} dal file {LOG_PATH}...")

    while True:
        line = f.readline()
        if line:
            try:
                # Invio log alla VPS
                requests.post(URL, data=line.encode("utf-8"))
                print("Inviato:", line.strip())
            except Exception as e:
                print("Errore invio log:", e)
        else:
            time.sleep(SLEEP_INTERVAL)
