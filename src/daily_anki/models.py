from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class Example:
    japanese: str
    english: str


@dataclass(frozen=True)
class Card:
    word: str
    readings: tuple[str, ...] = ()
    meanings: tuple[str, ...] = ()
    examples: tuple[Example, ...] = ()
    source_id: Optional[str] = None
    metadata: dict[str, str] = field(default_factory=dict)
    notes: str = ""
