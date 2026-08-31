import json
import sys

import pytest

from daily_anki import cli
from daily_anki.services import export_cards_from_words


def test_main_reports_operational_errors_without_traceback(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["daily-anki", "download-dictionary"])
    monkeypatch.setattr(cli, "download_latest", lambda path: (_ for _ in ()).throw(RuntimeError("download failed")))

    with pytest.raises(SystemExit) as error:
        cli.main()

    assert error.value.code == 1
    assert capsys.readouterr().err == "error: download failed\n"


def test_export_cards_from_words_builds_tsv(tmp_path):
    dictionary_path = tmp_path / "dictionary.json"
    dictionary_path.write_text(
        json.dumps({"words": [{"kanji": [{"text": "猫"}], "kana": [{"text": "ねこ"}], "sense": [{"gloss": [{"text": "cat"}]}]}]}),
        encoding="utf-8",
    )
    output_path = tmp_path / "exports" / "daily.tsv"

    card_count, missing = export_cards_from_words(["猫"], dictionary_path, output_path)

    assert card_count == 1
    assert missing == []
    assert output_path.exists()
    assert output_path.read_text(encoding="utf-8").startswith("猫\t")