from __future__ import annotations

from dataclasses import dataclass

from .gateways import AnkiGateway, SyncResult
from .models import Card


@dataclass(frozen=True)
class AnkiSyncConfig:
    """Anki sync configuration and options."""
    deck: str
    note_type: str
    dry_run: bool = False


class AnkiSyncService:
    """Service for Anki sync operations with configuration management."""

    def __init__(self, anki_gateway: AnkiGateway):
        self._gateway = anki_gateway

    def check_config(self, deck: str, note_type: str) -> int:
        """Check that deck and note type exist (read-only).
        
        Returns AnkiConnect version.
        Raises AnkiConnectError if configuration is invalid.
        """
        return self._gateway.check_configuration(deck, note_type)

    def ensure_config(self, deck: str, note_type: str) -> int:
        """Ensure deck and note type exist, creating them if needed.
        
        Returns AnkiConnect version.
        Raises AnkiConnectError if setup fails.
        """
        return self._gateway.ensure_configuration(deck, note_type)

    def sync(self, cards: list[Card], config: AnkiSyncConfig) -> SyncResult:
        """Sync cards to Anki using the provided configuration.
        
        For dry-run, ensures configuration exists first (to validate before changes).
        For actual sync, creates missing configuration automatically.
        
        Returns SyncResult with created/skipped card names.
        """
        if config.dry_run:
            # Dry-run: validate configuration exists but don't create
            self._gateway.check_configuration(config.deck, config.note_type)
        else:
            # Actual sync: create configuration if needed
            self._gateway.ensure_configuration(config.deck, config.note_type)
        
        return self._gateway.sync_cards(cards, config.deck, config.note_type, config.dry_run)
