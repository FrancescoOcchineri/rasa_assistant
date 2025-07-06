from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
import os
import shutil  
import logging
import requests

logger = logging.getLogger(__name__)

class ActionMostraContenuto(Action):
    def name(self) -> str:
        return "action_mostra_contenuto"
    
    def run(self, dispatcher, tracker, domain):
        disco = tracker.get_slot("disco")
        cartella = tracker.get_slot("cartella")

        if not disco or not cartella:
            dispatcher.utter_message(text="Percorso incompleto ricevuto. Specifica disco e cartella.")
            return []

        mount_map = {
            "C": "/mnt/c",
            "D": "/mnt/d",
            "R": "/mnt/r"
        }

        base_path = mount_map.get(disco.upper())
        if not base_path:
            dispatcher.utter_message(text=f"Disco '{disco}' non è montato nel container.")
            return []

        cartella_path = cartella.replace("\\", "/")

        percorso = os.path.join(base_path, cartella_path)
        percorso = os.path.normpath(percorso)

        if not os.path.exists(percorso):
            dispatcher.utter_message(text=f"Il percorso '{percorso}' non esiste. Ricalcolo impossibile.")
            return []

        if not os.path.isdir(percorso):
            dispatcher.utter_message(text=f"'{percorso}' non è una cartella valida.")
            return []

        try:
            files = os.listdir(percorso)
        except Exception as e:
            dispatcher.utter_message(text=f"Errore nella lettura della cartella: {e}")
            return []

        if not files:
            dispatcher.utter_message(text=f"La cartella '{percorso}' è vuota. Nessun dato da mostrare.")
            return []

        elenco = "\n".join(f"• {file}" for file in files)
        dispatcher.utter_message(text=f"Nella cartella '{percorso}' ho trovato:\n{elenco}")
        return []

class ActionEliminaFile(Action):
    def name(self) -> str:
        return "action_elimina_file"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[str, Any]) -> List[Dict[str, Any]]:

        file_path = tracker.get_slot("file")
        if not file_path:
            dispatcher.utter_message(text="Nessun file ricevuto da eliminare.")
            return []

        file_path = os.path.expanduser(file_path)

        if not os.path.isfile(file_path):
            dispatcher.utter_message(text=f"Il file '{file_path}' non esiste. Eliminazione fallita.")
            return []

        try:
            os.remove(file_path)
            dispatcher.utter_message(text=f"File '{file_path}' eliminato con successo.")
        except Exception as e:
            dispatcher.utter_message(text=f"Errore durante l'eliminazione: {str(e)}")
        return []

class ActionSpostaFile(Action):
    def name(self) -> str:
        return "action_sposta_file"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[str, Any]) -> List[Dict[str, Any]]:

        file_path = tracker.get_slot("file")
        dest_path = tracker.get_slot("destinazione")

        if not file_path or not dest_path:
            dispatcher.utter_message(text="Ricevuto input incompleto. File o destinazione mancante.")
            return []

        file_path = os.path.expanduser(file_path)
        dest_path = os.path.expanduser(dest_path)

        if not os.path.isfile(file_path):
            dispatcher.utter_message(text=f"Il file '{file_path}' non esiste.")
            return []

        if not os.path.isdir(dest_path):
            dispatcher.utter_message(text=f"La destinazione '{dest_path}' non esiste.")
            return []

        try:
            shutil.move(file_path, dest_path)
            dispatcher.utter_message(text=f"File spostato con successo in '{dest_path}'.")
        except Exception as e:
            dispatcher.utter_message(text=f"Errore durante lo spostamento: {str(e)}")
        return []
    
class ActionGenerateWithOllama(Action):
    def name(self):
        return "action_generate_with_ollama"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: dict) -> list:

        user_input = tracker.latest_message.get("text")
        if not user_input:
            dispatcher.utter_message(text="Non ho ricevuto nessun testo da elaborare.")
            return []

        try:
            response = requests.post(
                "http://ollama:11434/api/generate",
                json={
                    "model": "mistral",
                    "prompt": user_input,
                    "stream": False
                },
                timeout=120
            )
            response.raise_for_status()  
            data = response.json()
            reply = data.get("response", "").strip()

            if not reply:
                dispatcher.utter_message(text="Il modello non ha prodotto alcuna risposta.")
            else:
                dispatcher.utter_message(text=reply)

        except requests.exceptions.Timeout:
            logger.error("Timeout nella chiamata a Ollama")
            dispatcher.utter_message(text="Il servizio di generazione ha impiegato troppo tempo.")
        except requests.exceptions.RequestException as e:
            logger.error(f"Errore nella chiamata a Ollama: {e}")
            dispatcher.utter_message(text="Errore di comunicazione con il servizio di generazione.")
        except Exception as e:
            logger.error(f"Errore generico: {e}")
            dispatcher.utter_message(text="Errore imprevisto durante la generazione della risposta.")

        return []
