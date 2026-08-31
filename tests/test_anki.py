import json

import pytest

from daily_anki.anki import (
    AnkiConnectClient,
    AnkiConnectError,
    DEFAULT_DECK,
    DEFAULT_NOTE_TYPE,
    fields_for_card,
    sync_cards,
)
from daily_anki.models import Card, Example


def test_fields_for_card_matches_deck_contract():
    fields = fields_for_card(Card("猫", ("ねこ",), ("Ⓐ&nbsp; cat",), (Example("猫です。", "It is a cat."),)))
    assert fields["Target Word with Ruby"] == fields["Target Japanese Word"] == fields["Target Japanese Word 2"] == "猫"
    assert fields["Target Word Furigana"] == fields["Target Furigana 2"] == "ねこ"
    assert fields["English Definition (Lengthy Version)"] == ""
    assert fields["Target Romaji"] == fields["Audio"] == fields["Notes"] == ""
    assert fields["Japanese Example Sentence"] == "猫です。"
    assert fields["English Translation of Sentence"] == "It is a cat."


class FakeAnki:
    def __init__(self):
        self.added = []

    def deck_names(self):
        return [DEFAULT_DECK]

    def model_names(self):
        return [DEFAULT_NOTE_TYPE]

    def find_notes(self, query):
        return [1]

    def notes_info(self, note_ids):
        return [{"fields": {"Target Japanese Word": {"value": "猫"}}}]

    def add_note(self, deck, note_type, fields):
        self.added.append((deck, note_type, fields))
        return 2


def test_sync_skips_existing_and_adds_new_card():
    client = FakeAnki()
    result = sync_cards(client, [Card("猫"), Card("犬")], DEFAULT_DECK, DEFAULT_NOTE_TYPE)
    assert result.skipped == ("猫",)
    assert result.created == ("犬",)
    assert client.added[0][2]["Target Japanese Word"] == "犬"


def test_sync_dry_run_does_not_add_cards():
    client = FakeAnki()
    result = sync_cards(client, [Card("犬")], DEFAULT_DECK, DEFAULT_NOTE_TYPE, dry_run=True)
    assert result.created == ("犬",)
    assert client.added == []


def test_sync_requires_existing_deck():
    client = FakeAnki()
    with pytest.raises(AnkiConnectError, match="deck does not exist"):
        sync_cards(client, [Card("犬")], "Missing", DEFAULT_NOTE_TYPE)


class Response:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


def test_client_invokes_anki_connect():
    requests = []

    def opener(request):
        requests.append(json.loads(request.data.decode("utf-8")))
        return Response({"result": [DEFAULT_DECK], "error": None})

    assert AnkiConnectClient(opener=opener).deck_names() == [DEFAULT_DECK]
    assert requests[0]["action"] == "deckNames"
    assert requests[0]["version"] == 6
