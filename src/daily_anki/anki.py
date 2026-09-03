import json
import math
import os
from dataclasses import dataclass
from typing import Any, Callable, Optional
from urllib.error import URLError
from urllib.request import Request, urlopen

from .models import Card

# Configuration defaults (can be overridden by environment variables)
DEFAULT_ENDPOINT = os.getenv("ANKI_CONNECT_ENDPOINT", "http://127.0.0.1:8765")
DEFAULT_TIMEOUT = float(os.getenv("ANKI_CONNECT_TIMEOUT", "10.0"))
DEFAULT_DECK = os.getenv("ANKI_DECK", "Daily Life")
DEFAULT_NOTE_TYPE = os.getenv("ANKI_NOTE_TYPE", "Daily Anki")
FIELD_NAMES = (
    "Target Japanese Word",
    "Target Word Furigana",
    "English Definition",
    "Japanese Example Sentence",
    "English Translation of Sentence",
    "Notes",
)
DEFAULT_CARD_TEMPLATES = (
    {
        "Name": "Card 1",
        "Front": (
            "<div style='font-family: Arial; font-size: 14px;'>{{Target Word Furigana}}</div>"
            "<div style='font-family: MS Mincho, Arial; font-size: 35px;'>{{Target Japanese Word}}</div><br/>"
            "<hr>"
            "<div style='font-family: MS Mincho, Arial; font-size: 30px;'>{{furigana:Japanese Example Sentence}}</div>"
        ),
        "Back": (
            "<div style='font-family: Arial; font-size: 14px;'>{{Target Word Furigana}}</div>"
            "<div style='font-family: MS Mincho, Arial; font-size: 35px;'>{{Target Japanese Word}}</div>"
            "<div style='font-family: Arial; font-size: 20px; color:blue;'>{{English Definition}}</div>"
            "<hr>"
            "<div style='font-family: MS Mincho, Arial; font-size: 30px;'>{{furigana:Japanese Example Sentence}}</div>"
            "<div style='font-family: Arial; font-size: 20px;color:blue;'>{{English Translation of Sentence}}</div>"
            "<hr>"
            "{{Notes}}"
        ),
    },
)


class AnkiConnectError(RuntimeError):
    """Raised when AnkiConnect communication fails or returns an error."""

    pass


class AnkiConnectClient:
    """Client for communicating with AnkiConnect HTTP API.

    Provides methods to query Anki Desktop and manage decks, note types, and cards.
    Requires Anki Desktop with AnkiConnect add-on to be running.

    Configuration can be customized via environment variables:
    - ANKI_CONNECT_ENDPOINT: URL where AnkiConnect is running (default: http://127.0.0.1:8765)
    - ANKI_CONNECT_TIMEOUT: Request timeout in seconds (default: 10.0)
    """

    def __init__(
        self,
        endpoint: str = DEFAULT_ENDPOINT,
        opener: Callable[..., Any] = urlopen,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        """Initialize AnkiConnect client.

        Args:
            endpoint: URL where AnkiConnect HTTP API is running
            opener: (Testing only) Custom URL opener function
            timeout: Request timeout in seconds (must be positive finite)

        Raises:
            ValueError: If timeout is not a positive finite number
        """
        if not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("AnkiConnect timeout must be a positive finite number")
        self.endpoint = endpoint
        self.timeout = timeout
        self._opener = opener

    def invoke(self, action: str, **params: Any) -> Any:
        payload = json.dumps({"action": action, "version": 6, "params": params}).encode("utf-8")
        request = Request(self.endpoint, data=payload, headers={"Content-Type": "application/json"})
        try:
            with self._opener(request, timeout=self.timeout) as response:
                result = json.loads(response.read().decode("utf-8"))
        except (OSError, URLError, UnicodeDecodeError, json.JSONDecodeError) as error:
            raise AnkiConnectError(
                f"Could not connect to AnkiConnect at {self.endpoint}: {error}"
            ) from error
        if not isinstance(result, dict) or "error" not in result or "result" not in result:
            raise AnkiConnectError("AnkiConnect returned an invalid response")
        if result.get("error") is not None:
            raise AnkiConnectError(f"AnkiConnect {action} failed: {result['error']}")
        return result.get("result")

    def deck_names(self) -> list[str]:
        result = self.invoke("deckNames")
        if not isinstance(result, list) or not all(isinstance(deck, str) for deck in result):
            raise AnkiConnectError("AnkiConnect returned invalid deck names")
        return result

    def version(self) -> int:
        result = self.invoke("version")
        if not isinstance(result, int):
            raise AnkiConnectError("AnkiConnect returned an invalid version")
        return result

    def model_names(self) -> list[str]:
        result = self.invoke("modelNames")
        if not isinstance(result, list) or not all(isinstance(model, str) for model in result):
            raise AnkiConnectError("AnkiConnect returned invalid note type names")
        return result

    def model_field_names(self, model_name: str) -> list[str]:
        result = self.invoke("modelFieldNames", modelName=model_name)
        if not isinstance(result, list) or not all(isinstance(field, str) for field in result):
            raise AnkiConnectError("AnkiConnect returned invalid note type fields")
        return result

    def create_deck(self, deck: str) -> Any:
        return self.invoke("createDeck", deck=deck)

    def create_model(self, model_name: str) -> Any:
        css = """
.card {
 font-family: arial;
 font-size: 24px;
 text-align: center;
 color: black;
 background-color: white;
}
.card1 { background-color: #ffffff; }
.card2 { background-color: #ffffff; }
.card3 { background-color: #ffffff; }
"""
        return self.invoke(
            "createModel",
            modelName=model_name,
            inOrderFields=list(FIELD_NAMES),
            css=css,
            isCloze=False,
            cardTemplates=list(DEFAULT_CARD_TEMPLATES),
        )

    def find_notes(self, query: str) -> list[int]:
        result = self.invoke("findNotes", query=query)
        if not isinstance(result, list) or not all(isinstance(note_id, int) for note_id in result):
            raise AnkiConnectError("AnkiConnect returned invalid note IDs")
        return result

    def notes_info(self, note_ids: list[int]) -> list[dict[str, Any]]:
        result = self.invoke("notesInfo", notes=note_ids)
        if not isinstance(result, list) or not all(isinstance(note, dict) for note in result):
            raise AnkiConnectError("AnkiConnect returned invalid note information")
        return result

    def add_note(self, deck: str, note_type: str, fields: dict[str, str]) -> Optional[int]:
        return self.invoke(
            "addNote",
            note={
                "deckName": deck,
                "modelName": note_type,
                "fields": fields,
                "tags": [],
                "options": {"allowDuplicate": False, "duplicateScope": "deck"},
            },
        )


@dataclass(frozen=True)
class SyncResult:
    created: tuple[str, ...] = ()
    skipped: tuple[str, ...] = ()
    existing: tuple[str, ...] = ()
    failed: tuple[str, ...] = ()


def ensure_configuration(
    client: AnkiConnectClient, deck: str, note_type: str, create_missing: bool = True
) -> int:
    version = client.version()
    decks = client.deck_names()
    if deck not in decks:
        if create_missing:
            client.create_deck(deck)
        else:
            raise AnkiConnectError(f"Anki deck does not exist: {deck}")
    model_names = client.model_names()
    if note_type not in model_names:
        if create_missing:
            client.create_model(note_type)
        else:
            raise AnkiConnectError(f"Anki note type does not exist: {note_type}")
    else:
        actual_fields = client.model_field_names(note_type)
        missing_fields = [field for field in FIELD_NAMES if field not in actual_fields]
        if missing_fields:
            raise AnkiConnectError(
                f"Anki note type '{note_type}' is missing fields: {', '.join(missing_fields)}"
            )
    return version


def check_configuration(client: AnkiConnectClient, deck: str, note_type: str) -> int:
    return ensure_configuration(client, deck, note_type, create_missing=False)


def fields_for_card(card: Card) -> dict[str, str]:
    example = card.examples[0] if card.examples else None
    values = (
        card.word,
        "\n".join(card.readings),
        "<br>".join(card.meanings),
        example.japanese if example else "",
        example.english if example else "",
        card.notes,
    )
    return dict(zip(FIELD_NAMES, values))


def sync_cards(
    client: AnkiConnectClient, cards: list[Card], deck: str, note_type: str, dry_run: bool = False
) -> SyncResult:
    ensure_configuration(client, deck, note_type, create_missing=not dry_run)
    return sync_configured_cards(client, cards, deck, note_type, dry_run)


def sync_configured_cards(
    client: AnkiConnectClient, cards: list[Card], deck: str, note_type: str, dry_run: bool = False
) -> SyncResult:
    """Sync cards when the deck and note type have already been validated."""

    existing_ids = client.find_notes(
        f'deck:"{_escape_query_value(deck)}" note:"{_escape_query_value(note_type)}"'
    )
    existing_notes = client.notes_info(existing_ids) if existing_ids else []
    existing_words = {_normalize_duplicate_key(_note_word_value(note)) for note in existing_notes}
    created = []
    skipped = []
    existing = []
    failed = []
    for card in cards:
        duplicate_key = _normalize_duplicate_key(card.word)
        source_word = card.metadata.get("lookup_word", card.word)
        if duplicate_key in existing_words:
            skipped.append(source_word)
            existing.append(source_word)
            continue
        if dry_run:
            created.append(source_word)
            existing_words.add(duplicate_key)
            continue
        try:
            note_id = client.add_note(deck, note_type, fields_for_card(card))
        except AnkiConnectError:
            skipped.append(source_word)
            failed.append(source_word)
            continue
        if note_id is None:
            skipped.append(source_word)
            failed.append(source_word)
        else:
            created.append(source_word)
            existing_words.add(duplicate_key)
    return SyncResult(tuple(created), tuple(skipped), tuple(existing), tuple(failed))


def _note_word_value(note: dict[str, Any]) -> str:
    fields = note.get("fields", {})
    if not isinstance(fields, dict):
        return ""
    for field_name in ("Target Word with Ruby", "Target Japanese Word"):
        value = (
            fields.get(field_name, {}).get("value", "")
            if isinstance(fields.get(field_name), dict)
            else ""
        )
        if value:
            return value
    return ""


def _escape_query_value(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _normalize_duplicate_key(word: str) -> str:
    return "".join(
        chr(ord(character) - 0x60) if "ァ" <= character <= "ヶ" else character
        for character in word.strip()
    )
