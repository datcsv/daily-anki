import json
import sys

import pytest

from daily_anki import cli
from daily_anki.anki import SyncResult
from daily_anki.models import Card
from daily_anki.services import export_cards_from_words


def test_main_reports_operational_errors_without_traceback(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["daily-anki", "download-dictionary"])
    monkeypatch.setattr(
        cli, "download_latest", lambda path: (_ for _ in ()).throw(RuntimeError("download failed"))
    )

    with pytest.raises(SystemExit) as error:
        cli.main()

    assert error.value.code == 1
    assert capsys.readouterr().err == "error: download failed\n"


def test_anki_timeout_argument_is_validated():
    parser = cli.build_parser()

    assert parser.parse_args(["anki-check", "--timeout", "2.5"]).timeout == 2.5
    with pytest.raises(SystemExit):
        parser.parse_args(["anki-check", "--timeout", "0"])


def test_export_cards_from_words_builds_tsv(tmp_path):
    dictionary_path = tmp_path / "dictionary.json"
    dictionary_path.write_text(
        json.dumps(
            {
                "words": [
                    {
                        "kanji": [{"text": "猫"}],
                        "kana": [{"text": "ねこ"}],
                        "sense": [{"gloss": [{"text": "cat"}]}],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    output_path = tmp_path / "exports" / "daily.tsv"

    card_count, missing = export_cards_from_words(["猫"], dictionary_path, output_path)

    assert card_count == 1
    assert missing == []
    assert output_path.exists()
    assert output_path.read_text(encoding="utf-8").startswith("猫\t")


def test_clear_note_removes_only_created_or_existing_words(monkeypatch, tmp_path, capsys):
    class FakeNotesGateway:
        def __init__(self):
            self.removed = []
            self.cleared = False

        def fetch_words(self, folder, note_name):
            return ["猫", "犬", "鳥", "馬"]

        def remove_words(self, folder, note_name, words):
            self.removed.append((folder, note_name, words))

        def clear_note(self, folder, note_name):
            self.cleared = True

    class FakeDictionary:
        def lookup(self, word):
            cards = {
                "猫": Card("猫", metadata={"lookup_word": "猫"}),
                "犬": Card("犬", metadata={"lookup_word": "犬"}),
                "鳥": Card("鳥", metadata={"lookup_word": "鳥"}),
            }
            return cards.get(word)

    class FakeSyncService:
        def sync(self, cards, config):
            return SyncResult(created=("猫",), existing=("犬",), failed=("鳥",))

    parser = cli.build_parser()
    args = parser.parse_args(
        [
            "sync",
            "--note-name",
            "Daily Life",
            "--dictionary",
            str(tmp_path / "dictionary.json"),
            "--history",
            str(tmp_path / "history.jsonl"),
            "--clear-note",
        ]
    )
    notes_gateway = FakeNotesGateway()
    monkeypatch.setattr(cli.JMDictDictionarySource, "from_file", lambda path: FakeDictionary())

    cli._run(args, parser, notes_gateway, FakeSyncService())

    assert notes_gateway.removed == [("", "Daily Life", ["猫", "犬"])]
    assert notes_gateway.cleared is False
    assert "No match (1): 馬" in capsys.readouterr().out
