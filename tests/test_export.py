import csv

from daily_anki.export import write_tsv
from daily_anki.models import Card, Example


def test_write_tsv_escapes_tabs_and_keeps_examples(tmp_path):
    path = tmp_path / "cards.tsv"
    write_tsv([Card("猫", ("ねこ",), ("cat\tpet",), (Example("猫です。", "It is a cat."),))], path)
    with path.open(encoding="utf-8", newline="") as handle:
        row = next(csv.reader(handle, delimiter="\t"))
    assert len(row) == 12
    assert row[0] == row[4] == row[6] == "猫"
    assert row[5] == row[7] == "ねこ"
    assert row[1] == row[8] == row[10] == row[11] == ""
    assert row[2] == "猫です。"
    assert row[3] == "It is a cat."
    assert "cat\tpet" in row[9]

