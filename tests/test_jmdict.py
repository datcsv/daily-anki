import json
import io
import zipfile

from daily_anki.jmdict import Dictionary, _extract_json


def test_lookup_matches_kanji_and_collects_meanings_examples(tmp_path):
    path = tmp_path / "dictionary.json"
    path.write_text(json.dumps({"words": [{
        "id": "1", "kanji": [{"text": "猫"}], "kana": [{"text": "ねこ"}],
        "sense": [{"gloss": [{"text": "cat"}], "example": [{"japanese": "猫です。", "english": "It is a cat."}]}],
    }]}), encoding="utf-8")
    card = Dictionary.from_file(path).lookup("猫")
    assert card is not None
    assert card.readings == ("ねこ",)
    assert card.meanings == ("Ⓐ&nbsp; cat",)
    assert card.examples[0].english == "It is a cat."


def test_lookup_returns_none_for_missing_word():
    assert Dictionary([]).lookup("不存在") is None


def test_lookup_converts_katakana_reading_to_hiragana():
    card = Dictionary([{"kanji": [{"text": "珈琲"}], "kana": [{"text": "コーヒー"}]}]).lookup("珈琲")
    assert card is not None
    assert card.readings == ("こーひー",)


def test_extract_json_from_zip_asset():
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w") as compressed:
        compressed.writestr("jmdict-examples-eng.json", b'{"words": []}')
    assert _extract_json(archive.getvalue(), "jmdict-examples-eng.zip") == b'{"words": []}'
