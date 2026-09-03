import io
import json
import zipfile

from daily_anki.jmdict import Dictionary, _extract_json


def test_lookup_matches_kanji_and_collects_meanings_examples(tmp_path):
    path = tmp_path / "dictionary.json"
    path.write_text(
        json.dumps(
            {
                "words": [
                    {
                        "id": "1",
                        "kanji": [{"text": "猫"}],
                        "kana": [{"text": "ねこ"}],
                        "sense": [
                            {
                                "gloss": [{"text": "cat"}],
                                "example": [{"japanese": "猫です。", "english": "It is a cat."}],
                            }
                        ],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    card = Dictionary.from_file(path).lookup("猫")
    assert card is not None
    assert card.readings == ("ねこ",)
    assert card.meanings == ("Ⓐ&nbsp; cat",)
    assert card.examples[0].english == "It is a cat."


def test_lookup_returns_none_for_missing_word():
    assert Dictionary([]).lookup("不存在") is None


def test_lookup_converts_katakana_reading_to_hiragana():
    card = Dictionary([{"kanji": [{"text": "珈琲"}], "kana": [{"text": "コーヒー"}]}]).lookup(
        "珈琲"
    )
    assert card is not None
    assert card.readings == ("こーひー",)


def test_lookup_resolves_and_deduplicates_metadata_tags():
    card = Dictionary(
        [
            {
                "kanji": [{"text": "明白", "tags": ["ateji", "rK"]}],
                "kana": [{"text": "あからさま", "tags": ["sk"]}],
                "sense": [{"misc": ["uk"], "field": ["art"], "dialect": ["uk"]}],
            }
        ],
        {
            "rK": "rarely used kanji form",
            "uk": "word usually written using kana alone",
            "art": "art, aesthetics",
        },
    ).lookup("明白")
    assert card is not None
    assert card.notes == "word usually written using kana alone, art, aesthetics"


def test_lookup_deduplicates_readings_after_hiragana_conversion():
    card = Dictionary(
        [{"kana": [{"text": "むかつく"}, {"text": "ムカつく"}, {"text": "ムカツク"}]}]
    ).lookup("ムカつく")
    assert card is not None
    assert card.word == "むかつく"
    assert card.readings == ("むかつく",)


def test_lookup_prefers_common_kanji_spelling_and_first_reading():
    card = Dictionary(
        [
            {
                "kanji": [{"text": "旧字"}, {"text": "人気字", "common": True}],
                "kana": [{"text": "きゅうじ"}, {"text": "にんきじ", "common": True}],
            }
        ]
    ).lookup("旧字")
    assert card is not None
    assert card.word == "人気字"
    assert card.readings == ("にんきじ",)


def test_extract_json_from_zip_asset():
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w") as compressed:
        compressed.writestr("jmdict-examples-eng.json", b'{"words": []}')
    assert _extract_json(archive.getvalue(), "jmdict-examples-eng.zip") == b'{"words": []}'


def test_lookup_formats_pos_continuously_and_uses_first_entry():
    entries = [
        {
            "id": "first",
            "kanji": [{"text": "改める"}],
            "kana": [{"text": "あらためる"}],
            "sense": [
                {
                    "partOfSpeech": ["v1", "vt"],
                    "gloss": [{"text": "to change"}, {"text": "to alter"}],
                    "examples": [
                        {
                            "sentences": [
                                {"lang": "jpn", "text": "考えを改める。"},
                                {"lang": "eng", "text": "Change your thinking."},
                            ]
                        }
                    ],
                },
                {
                    "partOfSpeech": ["v1", "vt"],
                    "gloss": [{"text": "to reform"}],
                    "related": [["直す", "なおす", 1], ["直す", "なおす", 1]],
                },
            ],
        },
        {
            "id": "second",
            "kanji": [{"text": "改める"}],
            "sense": [{"gloss": [{"text": "wrong entry"}]}],
        },
    ]
    card = Dictionary(entries).lookup("改める")
    assert card is not None
    assert card.source_id == "first"
    assert card.meanings == (
        "Ichidan verb, transitive verb<br>Ⓐ&nbsp; to change, to alter",
        "Ⓑ&nbsp; to reform (see also: 直す)",
    )
    assert card.examples[0].english == "Change your thinking."


def test_lookup_separates_multiple_part_of_speech_types():
    card = Dictionary(
        [
            {
                "kana": [{"text": "あらため"}],
                "sense": [
                    {"partOfSpeech": ["suf"], "gloss": [{"text": "former"}, {"text": "previous"}]},
                    {
                        "partOfSpeech": ["n"],
                        "gloss": [{"text": "examination"}, {"text": "inspection"}],
                    },
                ],
            }
        ]
    ).lookup("あらため")
    assert card is not None
    assert card.meanings == (
        "suffix<br>Ⓐ&nbsp; former, previous",
        "noun<br>Ⓑ&nbsp; examination, inspection",
    )
