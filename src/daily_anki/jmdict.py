import hashlib
import io
import json
import os
import tarfile
import tempfile
import urllib.request
import zipfile
from pathlib import Path
from typing import Any, Optional

from .models import Card, Example

LATEST_RELEASE_API = "https://api.github.com/repos/scriptin/jmdict-simplified/releases/latest"
POS_LABELS = {
    "adj-f": "noun or verb acting prenominally",
    "adj-i": "i adjective",
    "adj-na": "na adjective (keiyodoshi)",
    "adj-no": "noun or verb acting prenominally",
    "adv": "adverb",
    "adv-to": "adverb taking the 'to' particle",
    "aux-adj": "auxiliary adjective",
    "aux-v": "auxiliary verb",
    "conj": "conjunction",
    "cop": "copula",
    "ctr": "counter",
    "exp": "expressions (phrases, clauses, etc.)",
    "int": "interjection (kandoushi)",
    "n": "noun",
    "n-adv": "adverbial noun",
    "n-pr": "proper noun",
    "num": "numeric",
    "pn": "pronoun",
    "pref": "noun, used as a prefix",
    "prt": "particle",
    "suf": "suffix",
    "v1": "Ichidan verb",
    "v5aru": "Godan verb - aru special class",
    "v5b": "Godan verb with `bu' ending",
    "v5g": "Godan verb with `gu' ending",
    "v5k": "Godan verb with `ku' ending",
    "v5k-s": "Godan verb - Iku/Yuku special class",
    "v5m": "Godan verb with `mu' ending",
    "v5n": "Godan verb with `nu' ending",
    "v5r": "Godan verb with `ru' ending",
    "v5s": "Godan verb with `su' ending",
    "v5t": "Godan verb with `tsu' ending",
    "v5u": "Godan verb with `u' ending",
    "v5r-i": "Godan verb with `ru' ending - irregular",
    "v5u-s": "Godan verb with `u' ending - special class",
    "v5uru": "Godan verb - Uru old class verb",
    "vi": "intransitive verb",
    "vk": "Kuru verb",
    "vs": "する verb - irregular",
    "vs-i": "する verb - irregular",
    "vs-s": "する verb - special class",
    "vt": "transitive verb",
    "adj-ix": "irregular i adjective",
    "adj-ku": "-ku adjective",
    "adj-nari": "archaic na adjective",
    "adj-pn": "prenominal adjective",
    "adj-shiku": "archaic shiku adjective",
    "adj-t": "taru adjective",
    "aux": "auxiliary",
    "n-pref": "prefix",
    "n-suf": "suffix",
    "unc": "unclassified word",
    "v-unspec": "unspecified verb",
    "v1-s": "Ichidan verb - special class",
    "v2a-s": "archaic nidan verb with `u' ending",
    "v2b-k": "archaic nidan verb with `bu' ending",
    "v2d-s": "archaic nidan verb with `zu' ending",
    "v2g-k": "archaic nidan verb with `gu' ending",
    "v2g-s": "archaic nidan verb with `gu' ending",
    "v2h-k": "archaic nidan verb with `fu' ending",
    "v2h-s": "archaic nidan verb with `bu' ending",
    "v2k-k": "archaic nidan verb with `ku' ending",
    "v2k-s": "archaic nidan verb with `ku' ending",
    "v2m-s": "archaic nidan verb with `mu' ending",
    "v2n-s": "archaic nidan verb with `nu' ending",
    "v2r-k": "archaic nidan verb with `ru' ending",
    "v2r-s": "archaic nidan verb with `ru' ending",
    "v2s-s": "archaic nidan verb with `su' ending",
    "v2t-k": "archaic nidan verb with `tsu' ending",
    "v2t-s": "archaic nidan verb with `tsu' ending",
    "v2w-s": "archaic nidan verb with `u' ending",
    "v2y-k": "archaic nidan verb with `yu' ending",
    "v2y-s": "archaic nidan verb with `yu' ending",
    "v2z-s": "archaic nidan verb with `zu' ending",
    "v4b": "Yodan verb with `bu' ending",
    "v4g": "Yodan verb with `gu' ending",
    "v4h": "Yodan verb with `fu' ending",
    "v4k": "Yodan verb with `ku' ending",
    "v4m": "Yodan verb with `mu' ending",
    "v4r": "Yodan verb with `ru' ending",
    "v4s": "Yodan verb with `su' ending",
    "v4t": "Yodan verb with `tsu' ending",
    "vn": "irregular nu verb",
    "vr": "irregular ru verb",
    "vs-c": "する verb - precursor to modern する",
    "vz": "ずる verb",
}


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
        canonical_word = _preferred_spelling(entry)
        meanings: list[str] = []
        examples: list[Example] = []
        meaning_index = 0
        previous_part_of_speech = None
        for sense in entry.get("sense", []):
            part_of_speech = _humanize_part_of_speech(sense.get("partOfSpeech", []))
            glosses = []
            for gloss in sense.get("gloss", []):
                text = gloss.get("text", "") if isinstance(gloss, dict) else str(gloss)
                if text:
                    glosses.append(text)
            if glosses:
                prefix = f"{part_of_speech}<br>" if part_of_speech and part_of_speech != previous_part_of_speech else ""
                related = _related_words(sense.get("related", []))
                related_text = f" (see also: {', '.join(related)})" if related else ""
                meanings.append(f"{prefix}{chr(0x24B6 + meaning_index)}&nbsp; {', '.join(glosses)}{related_text}")
                meaning_index += 1
                previous_part_of_speech = part_of_speech
            for example in sense.get("example", sense.get("examples", [])):
                japanese = example.get("japanese", "")
                english = example.get("english", "")
                if not japanese or not english:
                    sentences = {sentence.get("lang"): sentence.get("text", "") for sentence in example.get("sentences", [])}
                    japanese = sentences.get("jpn", "")
                    english = sentences.get("eng", "")
                if japanese and english:
                    examples.append(Example(japanese, english))
        preferred_reading = _preferred_reading(entry)
        readings = (_to_hiragana(preferred_reading),) if preferred_reading else ()
        return Card(
            word=canonical_word or word,
            readings=readings,
            meanings=tuple(meanings),
            examples=tuple(examples),
            source_id=str(entry.get("id", "")) or None,
            metadata={"lookup_word": word},
        )

    @staticmethod
    def _forms(entry: dict[str, Any]) -> set[str]:
        forms = {entry.get("word", ""), entry.get("reading", "")}
        forms.update(item.get("text", "") for item in entry.get("kanji", []))
        forms.update(item.get("text", "") for item in entry.get("kana", []))
        return {form for form in forms if form}


def _to_hiragana(text: str) -> str:
    return "".join(chr(ord(character) - 0x60) if "ァ" <= character <= "ヶ" else character for character in text)


def _preferred_spelling(entry: dict[str, Any]) -> str:
    kanji = entry.get("kanji", [])
    kana = entry.get("kana", [])
    if kanji:
        return next((item.get("text", "") for item in kanji if item.get("common")), kanji[0].get("text", ""))
    return next((item.get("text", "") for item in kana if item.get("common")), kana[0].get("text", "") if kana else "")


def _preferred_reading(entry: dict[str, Any]) -> str:
    kana = entry.get("kana", [])
    return next((item.get("text", "") for item in kana if item.get("common")), kana[0].get("text", "") if kana else "")


def _humanize_part_of_speech(codes: list[str]) -> str:
    labels = []
    for code in codes:
        label = POS_LABELS.get(code, code)
        if label not in labels:
            labels.append(label)
    return ", ".join(labels)


def _related_words(related: list[Any]) -> list[str]:
    words = []
    for relation in related:
        if isinstance(relation, list) and relation and isinstance(relation[0], str):
            word = relation[0]
            if word not in words:
                words.append(word)
    return words


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
    digest = asset.get("digest")
    if digest and digest.startswith("sha256:"):
        actual_digest = hashlib.sha256(archive).hexdigest()
        if actual_digest != digest.removeprefix("sha256:"):
            raise RuntimeError("JMDict archive checksum did not match GitHub's digest")
    dictionary_json = _extract_json(archive, asset["name"])
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix=f".{path.name}.", delete=False) as temporary:
        temporary.write(dictionary_json)
        temporary_path = Path(temporary.name)
    try:
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)
    return asset["name"]


def _extract_json(archive: bytes, asset_name: str) -> bytes:
    if asset_name.endswith(".zip"):
        with zipfile.ZipFile(io.BytesIO(archive)) as compressed:
            json_name = next(name for name in compressed.namelist() if name.endswith(".json"))
            return compressed.read(json_name)
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as compressed:
        json_member = next(member for member in compressed.getmembers() if member.name.endswith(".json"))
        extracted = compressed.extractfile(json_member)
        if extracted is None:
            raise RuntimeError("The JMDict archive did not contain readable JSON")
        return extracted.read()
