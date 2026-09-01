from __future__ import annotations

from pathlib import Path

from .export import write_tsv
from .gateways import DictionarySource


def export_cards_from_words(
    words: list[str],
    dictionary_path: Path | str,
    output_path: Path | str,
    dictionary_source: DictionarySource | None = None,
) -> tuple[int, list[str]]:
    """Export words to a TSV file using the provided dictionary source.

    If no dictionary_source is provided, creates a JMDict source from dictionary_path.
    """
    if dictionary_source is None:
        from .adapters import JMDictDictionarySource

        dictionary_source = JMDictDictionarySource.from_file(dictionary_path)

    cards = []
    missing = []
    for word in words:
        card = dictionary_source.lookup(word)
        if card is None:
            missing.append(word)
        else:
            cards.append(card)

    write_tsv(cards, Path(output_path))
    return len(cards), missing
