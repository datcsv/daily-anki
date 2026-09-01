import csv
from pathlib import Path

from .anki import fields_for_card
from .models import Card


def write_tsv(cards: list[Card], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        for card in cards:
            writer.writerow(fields_for_card(card).values())
