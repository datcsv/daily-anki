from __future__ import annotations

from pathlib import Path

from .anki import (
    AnkiConnectClient,
    check_configuration,
    ensure_configuration,
    sync_configured_cards,
)
from .gateways import AnkiGateway, DictionarySource, NotesGateway, SyncResult
from .jmdict import Dictionary as JMDictDictionary
from .models import Card
from .notes import clear_note as clear_note_impl
from .notes import fetch_words as fetch_words_impl
from .notes import remove_words as remove_words_impl


class AppleNotesGateway(NotesGateway):
    """Concrete implementation using Apple Notes via osascript.

    Uses AppleScript via osascript to read and modify notes in the macOS Notes app.
    Requires Notes app to be available and accessible via AppleScript.
    """

    def fetch_words(self, folder: str, note_name: str) -> list[str]:
        """Fetch words from an Apple Note.

        Args:
            folder: The Notes folder name (or empty string to search all folders)
            note_name: The exact name of the note to read (or empty string to search all notes)

        Returns:
            List of Japanese words extracted from the note's content.

        Raises:
            subprocess.CalledProcessError: If the osascript command fails.
        """
        return fetch_words_impl(folder, note_name)

    def clear_note(self, folder: str, note_name: str) -> None:
        """Clear the body of an Apple Note, preserving only the title.

        Args:
            folder: The Notes folder name (or empty string to search all folders)
            note_name: The exact name of the note to clear

        Raises:
            subprocess.CalledProcessError: If the osascript command fails.
        """
        clear_note_impl(folder, note_name)

    def remove_words(self, folder: str, note_name: str, words: list[str]) -> None:
        """Remove selected words from an Apple Note.

        Only removes complete vocabulary-list entries (list items, marked lines, or bare words).
        Preserves prose and links to prevent accidental data loss.

        Args:
            folder: The Notes folder name (or empty string to search all folders)
            note_name: The exact name of the note to modify
            words: List of Japanese words to remove from the note

        Raises:
            subprocess.CalledProcessError: If the osascript command fails.
        """
        remove_words_impl(folder, note_name, words)


class JMDictDictionarySource(DictionarySource):
    """Concrete implementation using JMDict Simplified.

    Provides dictionary lookups using the JMDict Simplified JSON format.
    Supports kanji, kana, and hiragana/katakana conversions.
    """

    def __init__(self, dictionary: JMDictDictionary):
        """Initialize with a loaded JMDict dictionary.

        Args:
            dictionary: A Dictionary instance containing loaded word entries.
        """
        self._dictionary = dictionary

    @classmethod
    def from_file(cls, path: Path | str) -> JMDictDictionarySource:
        """Load a dictionary from a JMDict JSON file.

        Args:
            path: Path to the jmdict-eng.json file

        Returns:
            A new JMDictDictionarySource instance

        Raises:
            FileNotFoundError: If the dictionary file does not exist
            ValueError: If the JSON format is invalid
        """
        return cls(JMDictDictionary.from_file(Path(path)))

    def lookup(self, word: str) -> Card | None:
        """Look up a Japanese word in the dictionary.

        Args:
            word: The Japanese word to look up (can be kanji or kana)

        Returns:
            A Card with meanings, readings, and examples; None if word not found
        """
        return self._dictionary.lookup(word)


class AnkiConnectGateway(AnkiGateway):
    """Concrete implementation using AnkiConnect.

    Communicates with Anki Desktop via the AnkiConnect HTTP API.
    Handles deck creation, note type setup, and card synchronization.
    """

    def __init__(self, client: AnkiConnectClient):
        """Initialize with an AnkiConnect client.

        Args:
            client: An AnkiConnectClient instance for API communication
        """
        self._client = client

    def ensure_configuration(self, deck: str, note_type: str) -> int:
        """Ensure the deck and note type exist, creating them if needed.

        Args:
            deck: Name of the Anki deck
            note_type: Name of the Anki note type (model)

        Returns:
            AnkiConnect version number

        Raises:
            AnkiConnectError: If unable to connect or validate configuration
        """
        return ensure_configuration(self._client, deck, note_type)

    def check_configuration(self, deck: str, note_type: str) -> int:
        """Check that the deck and note type exist (read-only).

        Args:
            deck: Name of the Anki deck
            note_type: Name of the Anki note type (model)

        Returns:
            AnkiConnect version number

        Raises:
            AnkiConnectError: If deck or note type is missing or invalid
        """
        return check_configuration(self._client, deck, note_type)

    def sync_cards(
        self, cards: list[Card], deck: str, note_type: str, dry_run: bool = False
    ) -> SyncResult:
        """Sync cards to Anki (assuming deck and note type already exist).

        Args:
            cards: List of Card objects to add to Anki
            deck: Name of the target Anki deck
            note_type: Name of the Anki note type (model)
            dry_run: If True, simulates sync without making changes

        Returns:
            SyncResult with counts of created, skipped, existing, and failed cards

        Raises:
            AnkiConnectError: If unable to connect to Anki
        """
        result = sync_configured_cards(self._client, cards, deck, note_type, dry_run)
        return SyncResult(
            created=result.created,
            skipped=result.skipped,
            existing=result.existing,
            failed=result.failed,
        )
