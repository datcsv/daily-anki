import csv

from daily_anki.export import write_tsv
from daily_anki.models import Card, Example


def test_write_tsv_escapes_tabs_and_keeps_examples(tmp_path):
    path = tmp_path / "cards.tsv"
    write_tsv([Card("猫", ("ねこ",), ("cat\tpet",), (Example("猫です。", "It is a cat."),))], path)
    with path.open(encoding="utf-8", newline="") as handle:
        row = next(csv.reader(handle, delimiter="\t"))
    assert len(row) == 6
    assert row[0] == "猫"
    assert row[1] == "ねこ"
    assert row[2] == "cat\tpet"
    assert row[3] == "猫です。"
    assert row[4] == "It is a cat."
    assert row[5] == ""
