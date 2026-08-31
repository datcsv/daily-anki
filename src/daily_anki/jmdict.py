import json
import io
import tarfile
import urllib.request
import zipfile
from pathlib import Path
from typing import Any, Optional

from .models import Card, Example

LATEST_RELEASE_API = "https://api.github.com/repos/scriptin/jmdict-simplified/releases/latest"


class Dictionary:
    def __init__(self, entries: list[dict[str, Any]]) -> None:
        self._index: dict[str, list[dict[str, Any]]] = {}
        for entry in entries:
            for form in self._forms(entry):
                self._index.setdefault(form, []).append(entry)

    @classmethod
    def from_file(cls, path: Path) -> "Dictionary":
        with path.open(encoding="utf-8") as handle:
            data = json.load(handle)
        entries = data.get("words", data) if isinstance(data, dict) else data
        if not isinstance(entries, list):
            raise ValueError("JMDict JSON must contain a 'words' list")
        return cls(entries)

    def lookup(self, word: str) -> Optional[Card]:
        word = word.strip()
        entries = self._index.get(word, [])
        if not entries:
            return None
        entry = entries[0]
        kanji = tuple(item.get("text", "") for item in entry.get("kanji", []))
        kana = tuple(item.get("text", "") for item in entry.get("kana", []))
        meanings: list[str] = []
        examples: list[Example] = []
        for sense in entry.get("sense", []):
            part_of_speech = ", ".join(sense.get("partOfSpeech", []))
            glosses = []
            for gloss in sense.get("gloss", []):
                text = gloss.get("text", "") if isinstance(gloss, dict) else str(gloss)
                if text:
                    glosses.append(text)
            if glosses:
                prefix = f"{part_of_speech}<br>" if part_of_speech else ""
                meanings.append(prefix + "<br>".join(f"{chr(0x24B6 + index)}&nbsp; {text}" for index, text in enumerate(glosses)))
            for example in sense.get("example", sense.get("examples", [])):
                japanese = example.get("japanese", "")
                english = example.get("english", "")
                if japanese and english:
                    examples.append(Example(japanese, english))
        return Card(word=word, readings=tuple(_to_hiragana(reading) for reading in (kana or kanji)), meanings=tuple(meanings), examples=tuple(examples), source_id=str(entry.get("id", "")) or None)

    @staticmethod
    def _forms(entry: dict[str, Any]) -> set[str]:
        forms = {entry.get("word", ""), entry.get("reading", "")}
        forms.update(item.get("text", "") for item in entry.get("kanji", []))
        forms.update(item.get("text", "") for item in entry.get("kana", []))
        return {form for form in forms if form}


def _to_hiragana(text: str) -> str:
    return "".join(chr(ord(character) - 0x60) if "ァ" <= character <= "ヶ" else character for character in text)


def download_latest(path: Path) -> str:
    request = urllib.request.Request(LATEST_RELEASE_API, headers={"User-Agent": "daily-anki"})
    with urllib.request.urlopen(request) as response:
        release = json.load(response)
    asset = next((item for item in release.get("assets", []) if "jmdict-examples-eng" in item.get("name", "") and item.get("name", "").endswith((".zip", ".tgz"))), None)
    if asset is None:
        raise RuntimeError("Could not find the English JMDict JSON asset in the latest release")
    path.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(asset["browser_download_url"]) as response:
        archive = response.read()
    if asset["name"].endswith(".zip"):
        with zipfile.ZipFile(io.BytesIO(archive)) as compressed:
            json_name = next(name for name in compressed.namelist() if name.endswith(".json"))
            path.write_bytes(compressed.read(json_name))
    else:
        with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as compressed:
            json_member = next(member for member in compressed.getmembers() if member.name.endswith(".json"))
            extracted = compressed.extractfile(json_member)
            if extracted is None:
                raise RuntimeError("The JMDict archive did not contain readable JSON")
            path.write_bytes(extracted.read())
    return asset["name"]
