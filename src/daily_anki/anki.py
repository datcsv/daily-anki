import json
from dataclasses import dataclass
from typing import Any, Callable, Optional
from urllib.error import URLError
from urllib.request import Request, urlopen

from .models import Card

DEFAULT_ENDPOINT = "http://127.0.0.1:8765"
DEFAULT_DECK = "Daily Life"
DEFAULT_NOTE_TYPE = "NihongoShark.com: JLPT Cramming Deck"
FIELD_NAMES = (
    "Target Word with Ruby",
    "English Definition (Lengthy Version)",
    "Japanese Example Sentence",
    "English Translation of Sentence",
    "Target Japanese Word",
    "Target Word Furigana",
    "Target Japanese Word 2",
    "Target Furigana 2",
    "Target Romaji",
    "Simple Definition",
    "Audio",
    "Notes",
)


class AnkiConnectError(RuntimeError):
    pass


class AnkiConnectClient:
    def __init__(self, endpoint: str = DEFAULT_ENDPOINT, opener: Callable[..., Any] = urlopen) -> None:
        self.endpoint = endpoint
        self._opener = opener

    def invoke(self, action: str, **params: Any) -> Any:
        payload = json.dumps({"action": action, "version": 6, "params": params}).encode("utf-8")
        request = Request(self.endpoint, data=payload, headers={"Content-Type": "application/json"})
        try:
            with self._opener(request) as response:
                result = json.loads(response.read().decode("utf-8"))
        except (OSError, URLError, json.JSONDecodeError) as error:
            raise AnkiConnectError(f"Could not connect to AnkiConnect at {self.endpoint}: {error}") from error
        if result.get("error") is not None:
            raise AnkiConnectError(f"AnkiConnect {action} failed: {result['error']}")
        return result.get("result")

    def deck_names(self) -> list[str]:
        return self.invoke("deckNames")

    def version(self) -> int:
        return self.invoke("version")

    def model_names(self) -> list[str]:
        return self.invoke("modelNames")

    def find_notes(self, query: str) -> list[int]:
        return self.invoke("findNotes", query=query)

    def notes_info(self, note_ids: list[int]) -> list[dict[str, Any]]:
        return self.invoke("notesInfo", notes=note_ids)

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


def check_configuration(client: AnkiConnectClient, deck: str, note_type: str) -> int:
    version = client.version()
    if deck not in client.deck_names():
        raise AnkiConnectError(f"Anki deck does not exist: {deck}")
    if note_type not in client.model_names():
        raise AnkiConnectError(f"Anki note type does not exist: {note_type}")
    return version


def fields_for_card(card: Card) -> dict[str, str]:
    example = card.examples[0] if card.examples else None
    values = (
        card.word,
        "",
        example.japanese if example else "",
        example.english if example else "",
        card.word,
        "\n".join(card.readings),
        card.word,
        "\n".join(card.readings),
        "",
        "<br>".join(card.meanings),
        "",
        "",
    )
    return dict(zip(FIELD_NAMES, values))


def sync_cards(client: AnkiConnectClient, cards: list[Card], deck: str, note_type: str, dry_run: bool = False) -> SyncResult:
    check_configuration(client, deck, note_type)

    existing_ids = client.find_notes(f'deck:"{deck}" note:"{note_type}"')
    existing_notes = client.notes_info(existing_ids) if existing_ids else []
    existing_words = {note.get("fields", {}).get("Target Japanese Word", {}).get("value", "") for note in existing_notes}
    created = []
    skipped = []
    for card in cards:
        if card.word in existing_words:
            skipped.append(card.word)
            continue
        if dry_run:
            created.append(card.word)
            existing_words.add(card.word)
            continue
        note_id = client.add_note(deck, note_type, fields_for_card(card))
        if note_id is None:
            skipped.append(card.word)
        else:
            created.append(card.word)
            existing_words.add(card.word)
    return SyncResult(tuple(created), tuple(skipped))
