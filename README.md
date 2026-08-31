# daily-anki

A small terminal workflow for turning Japanese words in Apple Notes into Anki cards using the JMDict Simplified dataset.

## Setup

Requires macOS, Python 3.9+, and permission for Terminal (or VS Code) to automate Notes.

```sh
./scripts/setup_venv.sh
source .venv/bin/activate
```

The script creates `.venv`, installs this project, and installs the optional test dependencies.

## First run

Download the latest English JMDict Simplified release with example sentences:

```sh
daily-anki download-dictionary --output data/jmdict-eng.json
```

Read words from a text file (one word per line) and write an Anki TSV:

```sh
daily-anki create --words-file words.txt --dictionary data/jmdict-eng.json --output exports/daily.tsv
```

Read a specific note from Apple Notes:

```sh
daily-anki create --note-name "Daily Life" --dictionary data/jmdict-eng.json --output exports/daily.tsv
```

Add `--notes-folder "Japanese"` to restrict the note lookup to a folder. If you provide only `--notes-folder`, all notes in that folder are read. Lines without a dictionary match are reported and skipped. In Anki, import the resulting file as tab-separated text and select the `NihongoShark.com: JLPT Cramming Deck` note type. The exporter writes all 12 fields in the deck's order: the three Japanese word fields are identical, the two furigana fields are identical and normalized to hiragana, examples use their Japanese and English fields, and English Definition (Lengthy Version), Target Romaji, Audio, and Notes remain empty.

Run checks with:

```sh
python -m pytest
```

The Apple Notes integration is isolated in `notes.py`; a future AnkiConnect/API integration can be added without changing lookup or export code.
