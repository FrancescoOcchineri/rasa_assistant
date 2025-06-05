from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
import os
import logging

logger = logging.getLogger(__name__)

class ActionMostraContenuto(Action):
    def name(self) -> str:
        return "action_mostra_contenuto"
    
    def run(self, dispatcher, tracker, domain):
        disco = tracker.get_slot("disco")
        cartella = tracker.get_slot("cartella")

        if not disco or not cartella:
            dispatcher.utter_message(text="Non ho ricevuto un percorso completo. Puoi ripetere?")
            return []

        # Costruisci il percorso completo, es: "C:\AMD" o "R:\assistente_vocale\dataset"
        percorso = f"{disco}:\\" + cartella.replace("/", "\\").replace("\\\\", "\\")

        # Normalizza percorso
        percorso = os.path.normpath(os.path.expanduser(percorso))

        if not os.path.exists(percorso):
            dispatcher.utter_message(text=f"Il percorso '{percorso}' non esiste.")
            return []

        if not os.path.isdir(percorso):
            dispatcher.utter_message(text=f"'{percorso}' non è una cartella.")
            return []

        try:
            files = os.listdir(percorso)
        except Exception as e:
            dispatcher.utter_message(text=f"Non posso leggere il contenuto della cartella: {e}")
            return []

        if not files:
            dispatcher.utter_message(text=f"La cartella '{percorso}' è vuota.")
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
            dispatcher.utter_message(text="Non ho ricevuto il percorso del file da eliminare.")
            return []

        file_path = os.path.expanduser(file_path)

        if not os.path.isfile(file_path):
            dispatcher.utter_message(text=f"Il file {file_path} non esiste.")
            return []

        try:
            os.remove(file_path)
            dispatcher.utter_message(text=f"File {file_path} eliminato.")
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
            dispatcher.utter_message(text="Non ho ricevuto il file o la destinazione.")
            return []

        file_path = os.path.expanduser(file_path)
        dest_path = os.path.expanduser(dest_path)

        if not os.path.isfile(file_path):
            dispatcher.utter_message(text=f"Il file {file_path} non esiste.")
            return []

        if not os.path.isdir(dest_path):
            dispatcher.utter_message(text=f"La destinazione {dest_path} non esiste.")
            return []

        try:
            shutil.move(file_path, dest_path)
            dispatcher.utter_message(text=f"File spostato in {dest_path}.")
        except Exception as e:
            dispatcher.utter_message(text=f"Errore durante lo spostamento: {str(e)}")
        return []
