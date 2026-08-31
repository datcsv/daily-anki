import argparse
from pathlib import Path

from .anki import AnkiConnectClient, DEFAULT_DECK, DEFAULT_ENDPOINT, DEFAULT_NOTE_TYPE, sync_cards
from .export import write_tsv
from .jmdict import Dictionary, download_latest
from .notes import fetch_words


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="daily-anki")
    commands = parser.add_subparsers(dest="command", required=True)
    download = commands.add_parser("download-dictionary", help="download the latest English JMDict JSON with examples")
    download.add_argument("--output", type=Path, default=Path("data/jmdict-eng.json"))
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
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "download-dictionary":
        print(f"Downloaded {download_latest(args.output)} to {args.output}")
        return 0
    if not args.words_file and not args.note_name and not args.notes_folder:
        build_parser().error("one of --words-file, --note-name, or --notes-folder is required")
    if args.words_file:
        words = [line.strip() for line in args.words_file.read_text(encoding="utf-8").splitlines() if line.strip()]
    else:
        words = fetch_words(args.notes_folder, args.note_name or "")
    dictionary = Dictionary.from_file(args.dictionary)
    cards = []
    missing = []
    for word in words:
        card = dictionary.lookup(word)
        if card is None:
            missing.append(word)
        else:
            cards.append(card)
    if args.command == "sync":
        result = sync_cards(AnkiConnectClient(args.endpoint), cards, args.deck, args.note_type, args.dry_run)
        action = "would add" if args.dry_run else "added"
        print(f"{action.capitalize()} {len(result.created)} cards to {args.deck}")
        if result.skipped:
            print(f"Skipped existing ({len(result.skipped)}): {', '.join(result.skipped)}")
    else:
        write_tsv(cards, args.output)
        print(f"Wrote {len(cards)} cards to {args.output}")
    if missing:
        print(f"No match ({len(missing)}): {', '.join(missing)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
