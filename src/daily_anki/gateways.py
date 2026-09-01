from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from .models import Card


class NotesGateway(ABC):
    """Abstract interface for fetching words from and clearing notes.

    Implementations handle reading Japanese words from various note sources
    and clearing or removing individual words from notes.
    """

    @abstractmethod
    def fetch_words(self, folder: str, note_name: str) -> list[str]:
        """Fetch Japanese words from a note.

        Args:
            folder: The note folder/container name (may be empty to search all)
            note_name: The exact name of the note (may be empty to search all)

        Returns:
            List of Japanese words extracted from the note's content.
        """
        pass

    @abstractmethod
    def clear_note(self, folder: str, note_name: str) -> None:
        """Clear the body of a note, preserving metadata like title.

        Args:
            folder: The note folder/container name
            note_name: The exact name of the note to clear
        """
        pass

    @abstractmethod
    def remove_words(self, folder: str, note_name: str, words: list[str]) -> None:
        """Remove selected words from a note.

        Implementations should only remove complete vocabulary-list entries,
        not arbitrary word substrings, to prevent accidental data loss.

        Args:
            folder: The note folder/container name
            note_name: The exact name of the note to modify
            words: List of words to remove
        """
        pass


class DictionarySource(ABC):
    """Abstract interface for dictionary lookup operations.

    Implementations provide word lookups with meanings, readings, and examples
    needed to populate Anki cards.
    """

    @abstractmethod
    def lookup(self, word: str) -> Card | None:
        """Look up a word and return a card or None if not found.

        Args:
            word: The word to look up (format depends on implementation)

        Returns:
            A Card with meanings and examples; None if not found
        """
        pass


class AnkiGateway(ABC):
    """Abstract interface for Anki operations.

    Handles communication with Anki Desktop, including configuration validation,
    deck/model management, and card synchronization.
    """

    @abstractmethod
    def ensure_configuration(self, deck: str, note_type: str) -> int:
        """Ensure deck and note type exist; return AnkiConnect version.

        Creates missing decks or note types as needed.

        Args:
            deck: Name of the Anki deck
            note_type: Name of the Anki note type (model)

        Returns:
            AnkiConnect API version

        Raises:
            AnkiConnectError: If unable to ensure configuration
        """
        pass

    @abstractmethod
    def check_configuration(self, deck: str, note_type: str) -> int:
        """Check that deck and note type exist; return AnkiConnect version.

        Does not create missing items (read-only check).

        Args:
            deck: Name of the Anki deck
            note_type: Name of the Anki note type (model)

        Returns:
            AnkiConnect API version

        Raises:
            AnkiConnectError: If deck or note type is missing or invalid
        """
        pass

    @abstractmethod
    def sync_cards(
        self, cards: list[Card], deck: str, note_type: str, dry_run: bool = False
    ) -> SyncResult:
        """Sync cards to Anki and return the result.

        Args:
            cards: List of Card objects to add
            deck: Name of the target Anki deck
            note_type: Name of the Anki note type (model)
            dry_run: If True, simulates sync without making changes

        Returns:
            SyncResult with counts and names of created/skipped/failed cards

        Raises:
            AnkiConnectError: If unable to connect to Anki
        """
        pass


@dataclass(frozen=True)
class SyncResult:
    created: tuple[str, ...] = ()
    skipped: tuple[str, ...] = ()
    existing: tuple[str, ...] = ()
    failed: tuple[str, ...] = ()
