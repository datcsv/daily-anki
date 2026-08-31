import json

import pytest

from daily_anki.anki import (
    AnkiConnectClient,
    AnkiConnectError,
    DEFAULT_DECK,
    DEFAULT_NOTE_TYPE,
    FIELD_NAMES,
    _escape_query_value,
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

    def version(self):
        return 6

    def model_names(self):
        return [DEFAULT_NOTE_TYPE]

    def model_field_names(self, model_name):
        return list(FIELD_NAMES)

    def create_deck(self, deck):
        return deck

    def create_model(self, model_name):
        return model_name

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


def test_sync_treats_null_add_result_as_skipped():
    client = FakeAnki()
    client.add_note = lambda deck, note_type, fields: None
    result = sync_cards(client, [Card("犬")], DEFAULT_DECK, DEFAULT_NOTE_TYPE)
    assert result.created == ()
    assert result.skipped == ("犬",)


def test_sync_matches_existing_katakana_spelling():
    client = FakeAnki()
    client.notes_info = lambda note_ids: [{"fields": {"Target Japanese Word": {"value": "ムカつく"}}}]
    result = sync_cards(client, [Card("むかつく")], DEFAULT_DECK, DEFAULT_NOTE_TYPE)
    assert result.created == ()
    assert result.skipped == ("むかつく",)


def test_sync_rejects_existing_note_type_with_missing_fields():
    client = FakeAnki()
    client.model_field_names = lambda model_name: []
    with pytest.raises(AnkiConnectError, match="missing fields"):
        sync_cards(client, [Card("犬")], DEFAULT_DECK, DEFAULT_NOTE_TYPE)


def test_sync_creates_missing_deck_and_note_type():
    client = FakeAnki()
    client.deck_names = lambda: []
    client.model_names = lambda: []
    created = []
    client.create_deck = lambda deck: created.append(("deck", deck))
    client.create_model = lambda model_name: created.append(("model", model_name))
    result = sync_cards(client, [Card("犬")], DEFAULT_DECK, DEFAULT_NOTE_TYPE)
    assert result.created == ("犬",)
    assert created == [("deck", DEFAULT_DECK), ("model", DEFAULT_NOTE_TYPE)]


def test_dry_run_does_not_create_missing_configuration():
    client = FakeAnki()
    client.deck_names = lambda: []
    with pytest.raises(AnkiConnectError, match="deck does not exist"):
        sync_cards(client, [Card("犬")], DEFAULT_DECK, DEFAULT_NOTE_TYPE, dry_run=True)


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


def test_client_rejects_malformed_response():
    def opener(request):
        return Response(["not", "an", "anki", "response"])

    with pytest.raises(AnkiConnectError, match="invalid response"):
        AnkiConnectClient(opener=opener).deck_names()


def test_client_rejects_invalid_typed_result():
    def opener(request):
        return Response({"result": {"not": "a list"}, "error": None})

    with pytest.raises(AnkiConnectError, match="invalid deck names"):
        AnkiConnectClient(opener=opener).deck_names()


def test_escape_query_value_handles_quotes_and_backslashes():
    assert _escape_query_value(r'Deck \"today\"') == r'Deck \\\"today\\\"'
