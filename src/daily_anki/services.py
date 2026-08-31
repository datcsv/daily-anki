from __future__ import annotations

from pathlib import Path

from .export import write_tsv
from .jmdict import Dictionary


def export_cards_from_words(words: list[str], dictionary_path: Path | str, output_path: Path | str) -> tuple[int, list[str]]:
    dictionary = Dictionary.from_file(Path(dictionary_path))
    cards = []
    missing = []
    for word in words:
        card = dictionary.lookup(word)
        if card is None:
            missing.append(word)
        else:
            cards.append(card)

    write_tsv(cards, Path(output_path))
    return len(cards), missing
