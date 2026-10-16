"""
Azioni che collegano TARS a Home Assistant.

AUTENTICAZIONE: DUE STRADE, CON RIPIEGO AUTOMATICO

1. Token esplicito in /share/rasa/.ha_token  (strada in uso)
   Un token di accesso a lunga durata generato dal profilo utente di Home
   Assistant. Le chiamate vanno direttamente a Core sulla porta 8123.

2. SUPERVISOR_TOKEN  (ripiego, se il file non esiste)
   Elegante -- ruotato dal sistema, vincolato al singolo add-on -- ma richiede
   che il manifest conceda sia hassio_api sia homeassistant_api, e nel nostro
   caso il proxy del Supervisor ha continuato a rispondere 401 nonostante
   entrambi i permessi dichiarati e il manifest ricaricato.

Il token sta in un FILE e non nelle opzioni dell'add-on deliberatamente:
modificare le opzioni comporta rileggere il manifest, con ricarica dello store
e ricostruzione. Un file in /share si aggiorna con uno scp e un riavvio.

GESTIONE ERRORI
La versione precedente raccoglieva ogni RequestException in un unico blocco,
quindi un 401 e un host irraggiungibile producevano lo stesso messaggio
inutile ("Home Assistant non risponde"). Qui le cause sono distinte, perche'
il messaggio deve orientare chi lo legge invece di costringerlo ai log.

RISOLUZIONE DEI NOMI
Gli entity_id (light.lampada_salotto_2) non sono cio' che una persona dice a
voce. Invece di mantenere a mano una tabella che invecchia a ogni dispositivo
aggiunto, interroghiamo /api/states a ogni richiesta e confrontiamo il nome
parlato con i friendly_name reali. Aggiungi una lampadina in Home Assistant e
TARS la conosce subito, senza riaddestrare nulla.
"""

import difflib
import json
import logging
import os
from typing import Any, Dict, List, Optional, Text

import requests
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher

logger = logging.getLogger(__name__)

PERCORSO_TOKEN = "/share/rasa/.ha_token"
URL_CORE = "http://homeassistant.local.hass.io:8123/api"
URL_PROXY = "http://supervisor/core/api"

DOMINI_COMMUTABILI = (
    "light",
    "switch",
    "fan",
    "input_boolean",
    "media_player",
    "climate",
    "automation",
)


class ErroreHA(Exception):
    """Errore con un messaggio già pronto per essere detto all'utente."""


def _token_da_file() -> Optional[Text]:
    try:
        with open(PERCORSO_TOKEN, "r", encoding="utf-8") as f:
            valore = f.read().strip()
        return valore or None
    except OSError:
        return None


class HomeAssistant:
    def __init__(self) -> None:
        esplicito = _token_da_file()
        if esplicito:
            self.token = esplicito
            self.base = URL_CORE
            self.origine = "token esplicito"
        else:
            self.token = os.environ.get("SUPERVISOR_TOKEN", "")
            self.base = URL_PROXY
            self.origine = "SUPERVISOR_TOKEN"

    def _headers(self) -> Dict[Text, Text]:
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

    def _chiama(self, metodo: Text, percorso: Text, corpo: Optional[dict] = None) -> Any:
        if not self.token:
            raise ErroreHA(
                "Non ho un token per Home Assistant. Serve il file "
                f"{PERCORSO_TOKEN}."
            )

        url = f"{self.base}{percorso}"
        try:
            r = requests.request(
                metodo, url, headers=self._headers(), json=corpo, timeout=10
            )
        except requests.exceptions.Timeout:
            raise ErroreHA("Home Assistant non ha risposto entro dieci secondi.")
        except requests.exceptions.ConnectionError:
            raise ErroreHA(f"Non riesco a raggiungere Home Assistant su {self.base}.")
        except requests.RequestException as e:
            logger.error("Errore imprevisto su %s: %s", url, e)
            raise ErroreHA("Errore imprevisto nel contattare Home Assistant.")

        if r.status_code in (401, 403):
            logger.error(
                "Autenticazione rifiutata su %s (origine: %s)", url, self.origine
            )
            raise ErroreHA(
                "Home Assistant ha rifiutato l'autenticazione. Il token non e' "
                "valido o e' scaduto."
            )
        if r.status_code == 404:
            raise ErroreHA(f"Home Assistant non conosce il percorso {percorso}.")
        if not r.ok:
            logger.error("Risposta %s da %s: %s", r.status_code, url, r.text[:200])
            raise ErroreHA(
                f"Home Assistant ha risposto con un errore {r.status_code}."
            )

        try:
            return r.json()
        except json.JSONDecodeError:
            return None

    def stati(self) -> List[Dict[Text, Any]]:
        return self._chiama("GET", "/states") or []

    def chiama_servizio(self, dominio: Text, servizio: Text, entity_id: Text) -> Any:
        return self._chiama(
            "POST", f"/services/{dominio}/{servizio}", {"entity_id": entity_id}
        )

    def trova(
        self,
        nome: Optional[Text],
        domini: Optional[tuple] = None,
        soglia: float = 0.55,
    ) -> Optional[Dict[Text, Any]]:
        """Risolve un nome parlato nell'entita' piu' somigliante.

        La sottostringa esatta ha precedenza sulla somiglianza approssimata:
        "salotto" deve preferire "Luce salotto" a "Luce sala" anche se la
        seconda ha una distanza di edit inferiore. Senza questa precedenza il
        confronto fuzzy da' risultati sorprendenti sui nomi brevi.
        """
        nome = (nome or "").strip().lower()
        if not nome:
            return None

        migliore, punteggio_migliore = None, 0.0
        for stato in self.stati():
            eid = stato.get("entity_id", "")
            dominio = eid.split(".")[0] if "." in eid else ""
            if domini and dominio not in domini:
                continue

            etichetta = (
                stato.get("attributes", {}).get("friendly_name") or eid
            ).lower()

            if nome in etichetta:
                punteggio = 0.95 + (len(nome) / max(len(etichetta), 1)) * 0.05
            else:
                punteggio = difflib.SequenceMatcher(None, nome, etichetta).ratio()

            if punteggio > punteggio_migliore:
                migliore, punteggio_migliore = stato, punteggio

        if punteggio_migliore < soglia:
            logger.info(
                "Nessuna entita' sopra soglia per '%s' (migliore: %.2f)",
                nome,
                punteggio_migliore,
            )
            return None
        return migliore


def _nome_amichevole(stato: Dict[Text, Any]) -> Text:
    return stato.get("attributes", {}).get("friendly_name") or stato.get("entity_id", "")


def _tono():
    """Import ritardato del frasario.

    personalita.py importa QUESTO modulo per riusare il client HomeAssistant:
    un import in cima creerebbe un ciclo. Ritardarlo alla prima chiamata lo
    evita, e ha un secondo effetto utile -- se il modulo della personalita'
    fosse assente o rotto, le azioni continuano a funzionare con frasi neutre
    invece di sollevare un'eccezione all'avvio.
    """
    try:
        try:
            from .personalita import fascia_corrente, frase
        except ImportError:
            from actions.personalita import fascia_corrente, frase
        return frase, fascia_corrente()
    except Exception as e:  # noqa: BLE001
        logger.debug("Frasario non disponibile: %s", e)
        return (lambda chiave, fascia, **fmt: fmt.get("nome", "")), "medio"


class ActionControllaDispositivo(Action):
    """Accende o spegne. La direzione si deduce dall'intent riconosciuto."""

    def name(self) -> Text:
        return "action_controlla_dispositivo"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        frase, fascia = _tono()

        nome = tracker.get_slot("dispositivo")
        if not nome:
            dispatcher.utter_message(text=frase("quale_dispositivo", fascia))
            return []

        intent = tracker.latest_message.get("intent", {}).get("name", "")
        accendere = intent == "accendi_dispositivo"
        servizio = "turn_on" if accendere else "turn_off"

        ha = HomeAssistant()
        try:
            stato = ha.trova(nome, domini=DOMINI_COMMUTABILI)
            if not stato:
                dispatcher.utter_message(
                    text=frase("non_trovato", fascia, nome=nome)
                )
                return []

            entity_id = stato["entity_id"]
            ha.chiama_servizio(entity_id.split(".")[0], servizio, entity_id)
        except ErroreHA as e:
            dispatcher.utter_message(text=str(e))
            return []

        dispatcher.utter_message(
            text=frase(
                "acceso" if accendere else "spento",
                fascia,
                nome=_nome_amichevole(stato),
            )
        )
        return []


class ActionStatoDispositivo(Action):
    """Riferisce lo stato di un'entita' qualsiasi, non solo commutabile."""

    def name(self) -> Text:
        return "action_stato_dispositivo"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        nome = tracker.get_slot("dispositivo")
        if not nome:
            dispatcher.utter_message(text="Lo stato di cosa, esattamente?")
            return []

        try:
            # Nessun filtro sui domini: qui vale anche un sensore o una porta.
            stato = HomeAssistant().trova(nome)
        except ErroreHA as e:
            dispatcher.utter_message(text=str(e))
            return []

        if not stato:
            dispatcher.utter_message(text=f"Non trovo '{nome}' tra le mie entita'.")
            return []

        valore = stato.get("state", "sconosciuto")
        unita = stato.get("attributes", {}).get("unit_of_measurement", "")

        # I valori tecnici letti ad alta voce suonano come errori, non come
        # risposte: "on" diventa "accesa".
        leggibile = {
            "on": "accesa",
            "off": "spenta",
            "open": "aperta",
            "closed": "chiusa",
            "home": "in casa",
            "not_home": "fuori",
            "unavailable": "non raggiungibile",
            "unknown": "in uno stato indeterminato",
        }.get(valore, valore)

        suffisso = f" {unita}" if unita else ""
        dispatcher.utter_message(
            text=f"{_nome_amichevole(stato)}: {leggibile}{suffisso}."
        )
        return []


class ActionTemperatura(Action):
    """Riporta le temperature note, o quella di un ambiente specifico."""

    def name(self) -> Text:
        return "action_temperatura"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        nome = tracker.get_slot("dispositivo")

        try:
            stati = HomeAssistant().stati()
        except ErroreHA as e:
            dispatcher.utter_message(text=str(e))
            return []

        # Selezione per device_class e non per nome: e' il modo corretto di
        # trovare "tutti i termometri" indipendentemente da come li hai
        # chiamati.
        termometri = [
            s
            for s in stati
            if s.get("attributes", {}).get("device_class") == "temperature"
            and s.get("state") not in ("unavailable", "unknown", None)
        ]

        frase, fascia = _tono()

        if not termometri:
            dispatcher.utter_message(text=frase("nessun_termometro", fascia))
            return []

        if nome:
            scelto, migliore = None, 0.0
            for s in termometri:
                etichetta = (
                    s.get("attributes", {}).get("friendly_name") or s["entity_id"]
                ).lower()
                p = (
                    1.0
                    if nome.lower() in etichetta
                    else difflib.SequenceMatcher(None, nome.lower(), etichetta).ratio()
                )
                if p > migliore:
                    scelto, migliore = s, p
            if scelto and migliore >= 0.55:
                unita = scelto.get("attributes", {}).get("unit_of_measurement", "")
                dispatcher.utter_message(
                    text=f"{_nome_amichevole(scelto)}: {scelto['state']}{unita}."
                )
                return []
            dispatcher.utter_message(text=frase("non_trovato", fascia, nome=nome))
            return []

        righe = [
            f"• {_nome_amichevole(s)}: {s['state']}"
            f"{s.get('attributes', {}).get('unit_of_measurement', '')}"
            for s in termometri[:8]
        ]
        dispatcher.utter_message(
            text=frase("temperature", fascia) + "\n" + "\n".join(righe)
        )
        return []
