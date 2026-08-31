from __future__ import annotations

from typing import Optional

from .gateways import NotesGateway, DictionarySource, AnkiGateway, SyncResult
from .models import Card
from .notes import fetch_words as fetch_words_impl, clear_note as clear_note_impl
from .jmdict import Dictionary as JMDictDictionary
from .anki import AnkiConnectClient, sync_cards as sync_cards_impl, check_configuration, ensure_configuration
from pathlib import Path


class AppleNotesGateway(NotesGateway):
    """Concrete implementation using Apple Notes via osascript."""

    def fetch_words(self, folder: str, note_name: str) -> list[str]:
        return fetch_words_impl(folder, note_name)

    def clear_note(self, folder: str, note_name: str) -> None:
        clear_note_impl(folder, note_name)


class JMDictDictionarySource(DictionarySource):
    """Concrete implementation using JMDict Simplified."""

    def __init__(self, dictionary: JMDictDictionary):
        self._dictionary = dictionary

    @classmethod
    def from_file(cls, path: Path | str) -> JMDictDictionarySource:
        return cls(JMDictDictionary.from_file(Path(path)))

    def lookup(self, word: str) -> Optional[Card]:
        return self._dictionary.lookup(word)


class AnkiConnectGateway(AnkiGateway):
    """Concrete implementation using AnkiConnect."""

    def __init__(self, client: AnkiConnectClient):
        self._client = client

    def ensure_configuration(self, deck: str, note_type: str) -> int:
        return ensure_configuration(self._client, deck, note_type)

    def check_configuration(self, deck: str, note_type: str) -> int:
        return check_configuration(self._client, deck, note_type)

    def sync_cards(
        self, cards: list[Card], deck: str, note_type: str, dry_run: bool = False
    ) -> SyncResult:
        result = sync_cards_impl(self._client, cards, deck, note_type, dry_run)
        return SyncResult(created=result.created, skipped=result.skipped)
