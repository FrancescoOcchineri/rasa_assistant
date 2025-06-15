from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
import os
import shutil  
import logging

logger = logging.getLogger(__name__)

class ActionMostraContenuto(Action):
    def name(self) -> str:
        return "action_mostra_contenuto"
    
    def run(self, dispatcher, tracker, domain):
        disco = tracker.get_slot("disco")
        cartella = tracker.get_slot("cartella")

        if not disco or not cartella:
            dispatcher.utter_message(text="TARS: Percorso incompleto ricevuto. Specifica disco e cartella.")
            return []

        mount_map = {
            "C": "/mnt/c",
            "D": "/mnt/d",
            "R": "/mnt/r"
        }

        base_path = mount_map.get(disco.upper())
        if not base_path:
            dispatcher.utter_message(text=f"TARS: Disco '{disco}' non è montato nel container.")
            return []

        cartella_path = cartella.replace("\\", "/")

        percorso = os.path.join(base_path, cartella_path)
        percorso = os.path.normpath(percorso)

        if not os.path.exists(percorso):
            dispatcher.utter_message(text=f"TARS: Il percorso '{percorso}' non esiste. Ricalcolo impossibile.")
            return []

        if not os.path.isdir(percorso):
            dispatcher.utter_message(text=f"TARS: '{percorso}' non è una cartella valida.")
            return []

        try:
            files = os.listdir(percorso)
        except Exception as e:
            dispatcher.utter_message(text=f"TARS: Errore nella lettura della cartella: {e}")
            return []

        if not files:
            dispatcher.utter_message(text=f"TARS: La cartella '{percorso}' è vuota. Nessun dato da mostrare.")
            return []

        elenco = "\n".join(f"• {file}" for file in files)
        dispatcher.utter_message(text=f"TARS: Nella cartella '{percorso}' ho trovato:\n{elenco}")
        return []

class ActionEliminaFile(Action):
    def name(self) -> str:
        return "action_elimina_file"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[str, Any]) -> List[Dict[str, Any]]:

        file_path = tracker.get_slot("file")
        if not file_path:
            dispatcher.utter_message(text="TARS: Nessun file ricevuto da eliminare.")
            return []

        file_path = os.path.expanduser(file_path)

        if not os.path.isfile(file_path):
            dispatcher.utter_message(text=f"TARS: Il file '{file_path}' non esiste. Eliminazione fallita.")
            return []

        try:
            os.remove(file_path)
            dispatcher.utter_message(text=f"TARS: File '{file_path}' eliminato con successo.")
        except Exception as e:
            dispatcher.utter_message(text=f"TARS: Errore durante l'eliminazione: {str(e)}")
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
            dispatcher.utter_message(text="TARS: Ricevuto input incompleto. File o destinazione mancante.")
            return []

        file_path = os.path.expanduser(file_path)
        dest_path = os.path.expanduser(dest_path)

        if not os.path.isfile(file_path):
            dispatcher.utter_message(text=f"TARS: Il file '{file_path}' non esiste.")
            return []

        if not os.path.isdir(dest_path):
            dispatcher.utter_message(text=f"TARS: La destinazione '{dest_path}' non esiste.")
            return []

        try:
            shutil.move(file_path, dest_path)
            dispatcher.utter_message(text=f"TARS: File spostato con successo in '{dest_path}'.")
        except Exception as e:
            dispatcher.utter_message(text=f"TARS: Errore durante lo spostamento: {str(e)}")
        return []
