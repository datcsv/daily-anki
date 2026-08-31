import daily_anki.notes as notes
from daily_anki.notes import parse_note_words


def test_parse_note_words_preserves_html_list_items_and_decodes_entities():
    html = "<div><h1>Daily Life</h1></div><div>- 猫 - cat</div><div><input type='checkbox'> 犬 &amp; 鳥</div><p>魚<br>馬</p>"
    assert parse_note_words(html) == ["猫", "犬", "鳥", "魚", "馬"]


def test_parse_note_words_ignores_english_symbols_urls_and_blank_lines():
    html = "<div>English explanation</div><div>https://jisho.org/search/猫</div><div>--- !!!</div><div>  </div><div>食べる (to eat)</div>"
    assert parse_note_words(html) == ["猫", "食べる"]


def test_clear_note_targets_named_note(monkeypatch):
    calls = []

    def fake_run(command, **kwargs):
        calls.append((command, kwargs))

    monkeypatch.setattr(notes.subprocess, "run", fake_run)
    notes.clear_note("Japanese", "Daily Life")
    assert calls[0][0][-2:] == ["Japanese", "Daily Life"]
    assert calls[0][1]["check"] is True


def test_remove_words_targets_named_note_with_only_completed_words(monkeypatch):
    calls = []

    def fake_run(command, **kwargs):
        calls.append((command, kwargs))

    monkeypatch.setattr(notes.subprocess, "run", fake_run)
    notes.remove_words("Japanese", "Daily Life", ["猫", "犬"])

    assert calls[0][0][-4:] == ["Japanese", "Daily Life", "猫", "犬"]
    assert calls[0][1]["check"] is True


def test_remove_words_does_not_call_apple_notes_without_words(monkeypatch):
    monkeypatch.setattr(notes.subprocess, "run", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError()))

    notes.remove_words("Japanese", "Daily Life", [])


def test_clear_script_preserves_note_title_heading():
    assert 'set noteTitle to name of currentNote' in notes.CLEAR_NOTE_SCRIPT
    assert 'set body of currentNote to "<div><h1>" & noteTitle & "</h1></div>"' in notes.CLEAR_NOTE_SCRIPT
