import argparse
import subprocess
from pathlib import Path
from typing import List, Tuple

from .anki import (
    AnkiConnectClient,
    DEFAULT_DECK,
    DEFAULT_ENDPOINT,
    DEFAULT_NOTE_TYPE,
    AnkiConnectError,
    ensure_configuration,
    sync_cards,
)
from .export import write_tsv
from .history import append_sync_event
from .jmdict import Dictionary, download_latest
from .notes import clear_note, fetch_words
from .models import Card


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="daily-anki")
    commands = parser.add_subparsers(dest="command", required=True)
    download = commands.add_parser("download-dictionary", help="download the latest English JMDict JSON with examples")
    download.add_argument("--output", type=Path, default=Path("data/jmdict-eng.json"))
    check = commands.add_parser("anki-check", help="check AnkiConnect, deck, and note type")
    check.add_argument("--deck", default=DEFAULT_DECK)
    check.add_argument("--note-type", default=DEFAULT_NOTE_TYPE)
    check.add_argument("--endpoint", default=DEFAULT_ENDPOINT)
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
    sync.add_argument("--clear-note", action="store_true", help="clear the selected Apple Note after a complete sync")
    return parser


def _load_words(args: argparse.Namespace, parser: argparse.ArgumentParser) -> list[str]:
    if not args.words_file and not args.note_name and not args.notes_folder:
        parser.error("one of --words-file, --note-name, or --notes-folder is required")
    if args.words_file:
        return [line.strip() for line in args.words_file.read_text(encoding="utf-8").splitlines() if line.strip()]
    return fetch_words(args.notes_folder, args.note_name or "")


def _lookup_cards(words: list[str], dictionary: Dictionary) -> Tuple[List[Card], List[str]]:
    cards = []
    missing = []
    for word in words:
        card = dictionary.lookup(word)
        if card is None:
            missing.append(word)
        else:
            cards.append(card)
    return cards, missing


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        return _run(args, parser)
    except (AnkiConnectError, OSError, RuntimeError, ValueError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"error: {error}\n")


def _run(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    if args.command == "download-dictionary":
        print(f"Downloaded {download_latest(args.output)} to {args.output}")
        return 0
    if args.command == "anki-check":
        version = ensure_configuration(AnkiConnectClient(args.endpoint), args.deck, args.note_type)
        print(f"AnkiConnect {version} is ready for deck '{args.deck}' and note type '{args.note_type}'")
        return 0
    if args.command == "sync" and args.clear_note and not args.note_name:
        parser.error("--clear-note requires --note-name")
    words = _load_words(args, parser)
    dictionary = Dictionary.from_file(args.dictionary)
    cards, missing = _lookup_cards(words, dictionary)
    if args.command == "sync":
        result = sync_cards(AnkiConnectClient(args.endpoint), cards, args.deck, args.note_type, args.dry_run)
        append_sync_event(args.history, args.deck, args.note_type, result, missing, args.dry_run)
        action = "would add" if args.dry_run else "added"
        print(f"{action.capitalize()} {len(result.created)} cards to {args.deck}")
        if result.skipped:
            print(f"Skipped existing ({len(result.skipped)}): {', '.join(result.skipped)}")
        if args.clear_note:
            if missing:
                print("Note was not cleared because some words had no dictionary match")
            elif not args.dry_run:
                clear_note(args.notes_folder, args.note_name)
                print(f"Cleared note body: {args.note_name}")
            else:
                print(f"Would clear note body: {args.note_name}")
    else:
        write_tsv(cards, args.output)
        print(f"Wrote {len(cards)} cards to {args.output}")
    if missing:
        print(f"No match ({len(missing)}): {', '.join(missing)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
