from daily_anki.notes import parse_note_words


def test_parse_note_words_preserves_html_list_items_and_decodes_entities():
    html = "<div>- 猫</div><div><input type='checkbox'> 犬 &amp; 鳥</div><p>魚<br>馬</p>"
    assert parse_note_words(html) == ["猫", "犬 & 鳥", "魚", "馬"]
