import csv
from pathlib import Path

from .models import Card


def write_tsv(cards: list[Card], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        for card in cards:
            example = card.examples[0] if card.examples else None
            writer.writerow([
                card.word,
                "",
                example.japanese if example else "",
                example.english if example else "",
                card.word,
                "\n".join(card.readings),
                card.word,
                "\n".join(card.readings),
                "",
                "<br>".join(card.meanings),
                "",
                "",
            ])
