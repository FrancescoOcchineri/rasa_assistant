"""
Sistema di personalita' di TARS: due parametri regolabili, persistenti, e
propagati a tutto cio' che l'assistente dice.

I DUE ASSI
Nel film TARS ha due manopole distinte, umorismo e onesta'. Sono ortogonali, e
insieme coprono quattro comportamenti diversi invece di due:

    ironia bassa  + sincerita' alta  -> referto asciutto, nudo e crudo
    ironia bassa  + sincerita' bassa -> burocratico, evasivo
    ironia alta   + sincerita' alta  -> pungente: dice tutto, e ride
    ironia alta   + sincerita' bassa -> ciarliero, gira intorno

PERSISTENZA, E PERCHE' NON BASTANO GLI SLOT
Gli slot di Rasa vivono nel tracker, cioe' nella singola conversazione. Home
Assistant apre una sessione nuova a ogni interazione con Assist: un livello
impostato oggi sarebbe dimenticato al turno successivo, che e' esattamente il
contrario di un tratto del carattere.

Lo stato vive quindi fuori dal tracker, con due fonti:

  1. Entita' input_number di Home Assistant, se esistono. E' la fonte
     autorevole quando presenti, perche' rende i parametri visibili in una
     dashboard, regolabili con uno slider e utilizzabili nelle automazioni
     ("dopo le 23, ironia al 10%").
  2. Un file JSON in /share, come ripiego e come cache. Funziona sempre,
     anche senza aver creato nulla in Home Assistant.

La scrittura va su entrambi; la lettura preferisce Home Assistant. Cosi' il
sistema funziona da subito e migliora se decidi di creare gli input_number.

PROPAGAZIONE
Il vero valore non e' la manopola: e' che tutto cambi. Le frasi generate dalle
azioni Python passano da frase(), che sceglie la variante in base alla fascia.
Le response statiche del domain usano invece le varianti condizionali di Rasa.
"""

import json
import logging
import os
import random
import re
from typing import Any, Dict, List, Optional, Text

from rasa_sdk import Action, Tracker
from rasa_sdk.events import SlotSet
from rasa_sdk.executor import CollectingDispatcher

try:
    from .ha_actions import ErroreHA, HomeAssistant
except ImportError:  # pragma: no cover - dipende da come rasa-sdk importa
    from actions.ha_actions import ErroreHA, HomeAssistant

logger = logging.getLogger(__name__)

PERCORSO_STATO = "/share/rasa/personalita.json"

ENTITA = {
    "ironia": "input_number.tars_ironia",
    "sincerita": "input_number.tars_sincerita",
}

PREDEFINITI = {"ironia": 90, "sincerita": 90}
PASSO = 20

ETICHETTE = {"ironia": "Ironia", "sincerita": "Sincerita'"}

PAROLE_PARAMETRO = {
    "ironia": ("ironia", "ironico", "umorismo", "umoristico", "spirito", "battut"),
    "sincerita": ("sincer", "onest", "franchezza", "diplomat", "diretto", "crudo"),
}

PAROLE_SU = ("alza", "aumenta", "aumentare", "alzare", "piu'", "più", "su", "massimo")
PAROLE_GIU = (
    "abbassa", "abbassare", "riduci", "ridurre", "diminuisci", "diminuire",
    "meno", "giu", "giù", "minimo",
)


# --------------------------------------------------------------------- stato


def grado(valore: int) -> Text:
    """Tre fasce. Le condizioni delle response confrontano valori discreti,
    quindi un numero libero produrrebbe cento casi invece di tre."""
    if valore < 34:
        return "basso"
    if valore < 67:
        return "medio"
    return "alto"


def _da_file() -> Dict[Text, int]:
    try:
        with open(PERCORSO_STATO, "r", encoding="utf-8") as f:
            dati = json.load(f)
        return {
            k: int(dati.get(k, v)) for k, v in PREDEFINITI.items()
        }
    except (OSError, ValueError, TypeError):
        return dict(PREDEFINITI)


def _su_file(valori: Dict[Text, int]) -> None:
    try:
        os.makedirs(os.path.dirname(PERCORSO_STATO), exist_ok=True)
        with open(PERCORSO_STATO, "w", encoding="utf-8") as f:
            json.dump(valori, f)
    except OSError as e:
        logger.warning("Non ho potuto scrivere %s: %s", PERCORSO_STATO, e)


def leggi() -> Dict[Text, int]:
    """Home Assistant se disponibile, altrimenti il file."""
    valori = _da_file()
    try:
        ha = HomeAssistant()
        stati = {s["entity_id"]: s for s in ha.stati()}
        for nome, eid in ENTITA.items():
            if eid in stati:
                try:
                    valori[nome] = int(float(stati[eid]["state"]))
                except (TypeError, ValueError):
                    pass
    except (ErroreHA, Exception) as e:  # noqa: BLE001 - la personalita' non
        # deve mai far fallire una risposta: se HA non risponde si usa il file.
        logger.debug("Lettura personalita' da HA non riuscita: %s", e)
    return valori


def scrivi(valori: Dict[Text, int]) -> None:
    _su_file(valori)
    try:
        ha = HomeAssistant()
        stati = {s["entity_id"] for s in ha.stati()}
        for nome, eid in ENTITA.items():
            if eid in stati:
                ha._chiama(  # noqa: SLF001 - client interno al progetto
                    "POST",
                    "/services/input_number/set_value",
                    {"entity_id": eid, "value": valori[nome]},
                )
    except (ErroreHA, Exception) as e:  # noqa: BLE001
        logger.debug("Scrittura personalita' su HA non riuscita: %s", e)


# ------------------------------------------------------------------- frasario
#
# Ogni voce ha tre varianti. Le azioni non scrivono piu' testo fisso: chiedono
# a frase() la versione adatta alla fascia corrente. Aggiungere un tono nuovo
# significa aggiungere una riga qui, non toccare la logica.

FRASI: Dict[Text, Dict[Text, List[Text]]] = {
    "acceso": {
        "basso": ["Acceso: {nome}."],
        "medio": ["Fatto, {nome} e' acceso.", "{nome} acceso."],
        "alto": [
            "{nome} acceso. Prego, non ringraziarmi.",
            "Luce fatta. Al settimo giorno mi riposo.",
        ],
    },
    "spento": {
        "basso": ["Spento: {nome}."],
        "medio": ["Fatto, {nome} e' spento.", "{nome} spento."],
        "alto": [
            "{nome} spento. Il risparmio energetico ringrazia.",
            "Buio su {nome}. Suggestivo.",
        ],
    },
    "non_trovato": {
        "basso": ["Nessuna corrispondenza per '{nome}'."],
        "medio": ["Non trovo '{nome}'. Controlla il nome in Home Assistant."],
        "alto": [
            "'{nome}' non esiste. Nemmeno vagamente. Riprova.",
            "Ho cercato '{nome}' con impegno. Non c'e'.",
        ],
    },
    "temperature": {
        "basso": ["Temperature:"],
        "medio": ["Ecco le temperature rilevate:"],
        "alto": ["Bollettino termico, come richiesto:"],
    },
    "nessun_termometro": {
        "basso": ["Nessun sensore di temperatura."],
        "medio": ["Non ho sensori di temperatura disponibili."],
        "alto": [
            "Non ho termometri. Posso solo intuire, e non e' il mio mestiere.",
        ],
    },
    "quale_dispositivo": {
        "basso": ["Specifica il dispositivo."],
        "medio": ["Quale dispositivo?"],
        "alto": ["Quale dispositivo? Non leggo nel pensiero."],
    },
}


def fascia_corrente() -> Text:
    """Fascia di ironia leggendo il solo file: nessuna chiamata di rete.

    Serve nei percorsi caldi -- accendere una luce, leggere una temperatura --
    dove un giro HTTP in piu' per scegliere il tono di una frase non e'
    giustificato. Il file e' sempre allineato, perche' scrivi() lo aggiorna a
    ogni modifica; l'unico caso di scostamento e' uno slider mosso a mano in
    Home Assistant, che verra' recuperato alla prossima lettura autorevole.
    """
    return grado(_da_file()["ironia"])


def frase(chiave: Text, fascia: Text, **fmt: Any) -> Text:
    """Restituisce una variante adatta alla fascia, formattata.

    Il ripiego su 'medio' e sulla chiave assente evita che un frasario
    incompleto trasformi una risposta in un'eccezione: la personalita' e'
    un ornamento, non deve poter rompere una funzione.
    """
    varianti = FRASI.get(chiave, {}).get(fascia)
    if not varianti:
        varianti = FRASI.get(chiave, {}).get("medio") or ["{nome}"]
    return random.choice(varianti).format(**fmt)


# -------------------------------------------------------------------- azioni


def _livello_richiesto(tracker: Tracker) -> Optional[int]:
    for e in tracker.latest_message.get("entities", []):
        if e.get("entity") == "livello":
            try:
                return int(re.sub(r"\D", "", str(e.get("value"))))
            except (TypeError, ValueError):
                continue
    return None


def _parametro_richiesto(testo: Text) -> Optional[Text]:
    """Quale manopola. Riconosciuto per parole chiave e non per entita':
    con pochi esempi di addestramento l'estrazione sarebbe inaffidabile,
    mentre la presenza di 'ironia' o 'sincerita' nella frase e' certa."""
    for nome, parole in PAROLE_PARAMETRO.items():
        if any(par in testo for par in parole):
            return nome
    return None


class ActionImpostaPersonalita(Action):
    def name(self) -> Text:
        return "action_imposta_personalita"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        testo = (tracker.latest_message.get("text") or "").lower()
        valori = leggi()

        parametro = _parametro_richiesto(testo) or "ironia"
        attuale = valori[parametro]
        richiesto = _livello_richiesto(tracker)

        if richiesto is not None:
            nuovo = richiesto
        elif any(par in testo for par in PAROLE_SU):
            nuovo = 100 if "massimo" in testo else attuale + PASSO
        elif any(par in testo for par in PAROLE_GIU):
            nuovo = 0 if "minimo" in testo else attuale - PASSO
        else:
            # Intent riconosciuto senza numero ne' direzione. Su un parametro
            # che l'utente ha voluto controllare esplicitamente, chiedere e'
            # meglio che indovinare.
            dispatcher.utter_message(
                text=f"A quanto? {ETICHETTE[parametro]} e' al {attuale}%. "
                "Dimmi una percentuale, oppure alza o abbassa."
            )
            return []

        # Limite 0-100 anche se chiedi il 300%: TARS non e' un cabarettista.
        nuovo = max(0, min(100, nuovo))
        valori[parametro] = nuovo
        scrivi(valori)

        fascia = grado(valori["ironia"])
        sincero = valori["sincerita"] >= 67

        if nuovo == attuale:
            testo_risposta = f"{ETICHETTE[parametro]} era gia' al {nuovo}%."
        elif parametro == "ironia":
            testo_risposta = {
                "basso": f"Ironia al {nuovo}%. Modalita' sobria. Sara' noioso "
                         "per entrambi.",
                "medio": f"Ironia al {nuovo}%. Un compromesso ragionevole.",
                "alto": f"Ironia al {nuovo}%. Ti avviso: a questo livello "
                        "commento anche le tue scelte.",
            }[grado(nuovo)]
        else:
            testo_risposta = {
                "basso": f"Sincerita' al {nuovo}%. Da ora sceglierò le parole "
                         "con cura. Molta cura.",
                "medio": f"Sincerita' al {nuovo}%. Ti dirò le cose, con un "
                         "filtro.",
                "alto": f"Sincerita' al {nuovo}%. Non chiedermi se ti sta "
                        "bene quel maglione.",
            }[grado(nuovo)]

        logger.info(
            "Personalita': %s %s%% -> %s%% | ironia=%s sincerita=%s",
            parametro, attuale, nuovo, valori["ironia"], valori["sincerita"],
        )

        dispatcher.utter_message(text=testo_risposta)

        # Gli slot esistono per alimentare le varianti condizionali del domain
        # e il templating: la verita' persistente sta fuori dal tracker.
        return [
            SlotSet("ironia_livello", str(valori["ironia"])),
            SlotSet("ironia_grado", fascia),
            SlotSet("sincerita_livello", str(valori["sincerita"])),
            SlotSet("sincerita_alta", sincero),
        ]


class ActionStatoPersonalita(Action):
    def name(self) -> Text:
        return "action_stato_personalita"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        valori = leggi()
        i, s = valori["ironia"], valori["sincerita"]

        chiusura = {
            ("alto", True): "Combinazione pungente: dico tutto, e ne rido.",
            ("alto", False): "Ciarliero e diplomatico. Girero' intorno, ma con brio.",
            ("medio", True): "Equilibrato e diretto.",
            ("medio", False): "Equilibrato e prudente.",
            ("basso", True): "Asciutto e senza filtri. Referto, non conversazione.",
            ("basso", False): "Sobrio e cauto. Praticamente un modulo da compilare.",
        }[(grado(i), s >= 67)]

        dispatcher.utter_message(
            text=f"Ironia al {i}%, sincerita' al {s}%. {chiusura}"
        )
        return [
            SlotSet("ironia_livello", str(i)),
            SlotSet("ironia_grado", grado(i)),
            SlotSet("sincerita_livello", str(s)),
            SlotSet("sincerita_alta", s >= 67),
        ]


class ActionReimpostaPersonalita(Action):
    def name(self) -> Text:
        return "action_reimposta_personalita"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        valori = dict(PREDEFINITI)
        scrivi(valori)
        dispatcher.utter_message(
            text="Parametri riportati ai valori di fabbrica: ironia 90%, "
            "sincerita' 90%. Come mi ha costruito Francesco, prima dei "
            "ripensamenti."
        )
        return [
            SlotSet("ironia_livello", str(valori["ironia"])),
            SlotSet("ironia_grado", grado(valori["ironia"])),
            SlotSet("sincerita_livello", str(valori["sincerita"])),
            SlotSet("sincerita_alta", True),
        ]
