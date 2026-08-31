import argparse
import subprocess
from pathlib import Path

from .anki import (
    AnkiConnectClient,
    DEFAULT_DECK,
    DEFAULT_ENDPOINT,
    DEFAULT_NOTE_TYPE,
    AnkiConnectError,
)
from .jmdict import download_latest
from .adapters import (
    AppleNotesGateway,
    JMDictDictionarySource,
    AnkiConnectGateway,
)
from .anki_sync_service import AnkiSyncService, AnkiSyncConfig
from .gateways import NotesGateway, AnkiGateway
from .history import append_sync_event
from .models import Card
from .services import export_cards_from_words


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="daily-anki")
    commands = parser.add_subparsers(dest="command", required=True)
    download = commands.add_parser("download-dictionary", help="download the latest English JMDict JSON with examples")
    download.add_argument("--output", type=Path, default=Path("data/jmdict-eng.json"))
    check = commands.add_parser("anki-check", help="check AnkiConnect, deck, and note type")
    check.add_argument("--deck", default=DEFAULT_DECK)
    check.add_argument("--note-type", default=DEFAULT_NOTE_TYPE)
    check.add_argument("--endpoint", default=DEFAULT_ENDPOINT)
    setup = commands.add_parser("anki-setup", help="create the Anki deck and note type if missing")
    setup.add_argument("--deck", default=DEFAULT_DECK)
    setup.add_argument("--note-type", default=DEFAULT_NOTE_TYPE)
    setup.add_argument("--endpoint", default=DEFAULT_ENDPOINT)
    create = commands.add_parser("create", help="create an Anki TSV from words or Apple Notes")
    sync = commands.add_parser("sync", help="create cards directly in Anki Desktop through AnkiConnect")
    for command in (create, sync):
        source = command.add_mutually_exclusive_group()
        source.add_argument("--words-file", type=Path)
        source.add_argument("--note-name", metavar="NOTE")
        command.add_argument("--notes-folder", default="", metavar="FOLDER")
        command.add_argument("--dictionary", type=Path, required=True)
    create.add_argument("--output", type=Path, default=Path("exports/daily.tsv"))
    sync.add_argument("--deck", default=DEFAULT_DECK)
    sync.add_argument("--note-type", default=DEFAULT_NOTE_TYPE)
    sync.add_argument("--endpoint", default=DEFAULT_ENDPOINT)
    sync.add_argument("--dry-run", action="store_true", help="show what would be added without changing Anki")
    sync.add_argument("--history", type=Path, default=Path("data/sync-history.jsonl"))
    sync.add_argument("--clear-note", action="store_true", help="remove words created in Anki or already in the deck from the selected Apple Note")
    return parser


def _load_words(args: argparse.Namespace, parser: argparse.ArgumentParser, notes_gateway: NotesGateway) -> list[str]:
    if not args.words_file and not args.note_name and not args.notes_folder:
        parser.error("one of --words-file, --note-name, or --notes-folder is required")
    if args.words_file:
        return [line.strip() for line in args.words_file.read_text(encoding="utf-8").splitlines() if line.strip()]
    return notes_gateway.fetch_words(args.notes_folder, args.note_name or "")


def _lookup_cards(words: list[str], dictionary_source) -> tuple[list[Card], list[str]]:
    cards = []
    missing = []
    for word in words:
        card = dictionary_source.lookup(word)
        if card is None:
            missing.append(word)
        else:
            cards.append(card)
    return cards, missing


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        notes_gateway = AppleNotesGateway()
        anki_gateway = AnkiConnectGateway(AnkiConnectClient(args.endpoint if hasattr(args, "endpoint") else DEFAULT_ENDPOINT))
        anki_sync_service = AnkiSyncService(anki_gateway)
        return _run(args, parser, notes_gateway, anki_sync_service)
    except (AnkiConnectError, OSError, RuntimeError, ValueError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"error: {error}\n")


def _run(args: argparse.Namespace, parser: argparse.ArgumentParser, notes_gateway: NotesGateway, anki_sync_service: AnkiSyncService) -> int:
    if args.command == "download-dictionary":
        print(f"Downloaded {download_latest(args.output)} to {args.output}")
        return 0
    if args.command == "anki-check":
        version = anki_sync_service.check_config(args.deck, args.note_type)
        print(f"AnkiConnect {version} is ready for deck '{args.deck}' and note type '{args.note_type}'")
        return 0
    if args.command == "anki-setup":
        version = anki_sync_service.ensure_config(args.deck, args.note_type)
        print(f"AnkiConnect {version} is configured for deck '{args.deck}' and note type '{args.note_type}'")
        return 0
    if args.command == "sync" and args.clear_note and not args.note_name:
        parser.error("--clear-note requires --note-name")
    words = _load_words(args, parser, notes_gateway)
    dictionary_source = JMDictDictionarySource.from_file(args.dictionary)
    cards, missing = _lookup_cards(words, dictionary_source)
    if args.command == "sync":
        config = AnkiSyncConfig(deck=args.deck, note_type=args.note_type, dry_run=args.dry_run)
        result = anki_sync_service.sync(cards, config)
        append_sync_event(args.history, args.deck, args.note_type, result, missing, args.dry_run)
        action = "would add" if args.dry_run else "added"
        print(f"{action.capitalize()} {len(result.created)} cards to {args.deck}")
        if result.existing:
            print(f"Skipped existing ({len(result.existing)}): {', '.join(result.existing)}")
        if result.failed:
            print(f"Not added ({len(result.failed)}): {', '.join(result.failed)}")
        if args.clear_note:
            removable_words = [*result.created, *result.existing]
            if not args.dry_run and removable_words:
                notes_gateway.remove_words(args.notes_folder, args.note_name, removable_words)
                print(f"Removed {len(removable_words)} synced words from note: {args.note_name}")
            else:
                action = "Would remove" if args.dry_run else "No words removed from"
                print(f"{action} note: {args.note_name}")
    else:
        card_count, missing = export_cards_from_words(words, args.dictionary, args.output, dictionary_source)
        print(f"Wrote {card_count} cards to {args.output}")
    if missing:
        print(f"No match ({len(missing)}): {', '.join(missing)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
