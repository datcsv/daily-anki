from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from .models import Card


class NotesGateway(ABC):
    """Abstract interface for fetching words from and clearing notes."""

    @abstractmethod
    def fetch_words(self, folder: str, note_name: str) -> list[str]:
        """Fetch words from a note."""
        pass

    @abstractmethod
    def clear_note(self, folder: str, note_name: str) -> None:
        """Clear the body of a note."""
        pass

    @abstractmethod
    def remove_words(self, folder: str, note_name: str, words: list[str]) -> None:
        """Remove selected words from a note."""
        pass


class DictionarySource(ABC):
    """Abstract interface for dictionary lookup operations."""

    @abstractmethod
    def lookup(self, word: str) -> Card | None:
        """Look up a word and return a card or None if not found."""
        pass


class AnkiGateway(ABC):
    """Abstract interface for Anki operations."""

    @abstractmethod
    def ensure_configuration(self, deck: str, note_type: str) -> int:
        """Ensure deck and note type exist; return AnkiConnect version."""
        pass

    @abstractmethod
    def check_configuration(self, deck: str, note_type: str) -> int:
        """Check that deck and note type exist; return AnkiConnect version."""
        pass

    @abstractmethod
    def sync_cards(
        self, cards: list[Card], deck: str, note_type: str, dry_run: bool = False
    ) -> SyncResult:
        """Sync cards to Anki and return the result."""
        pass


@dataclass(frozen=True)
class SyncResult:
    created: tuple[str, ...] = ()
    skipped: tuple[str, ...] = ()
    existing: tuple[str, ...] = ()
    failed: tuple[str, ...] = ()
