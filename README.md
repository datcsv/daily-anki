# daily-anki

`daily-anki` helps you turn Japanese vocabulary from Apple Notes or a word list into Anki flashcards.

It looks up each word in the JMDict dictionary, builds a ready-to-import TSV file, and can optionally send cards directly to Anki using AnkiConnect.

## What it does

- Reads words from a text file or from notes in Apple Notes
- Looks up dictionary entries and extracts useful meaning data
- Exports cards in a format that can be imported into Anki
- Can sync the cards directly to Anki if AnkiConnect is running

## Requirements

- macOS
- Python 3.9+
- Anki Desktop (optional, for syncing cards directly)
- AnkiConnect add-on (optional, for sync)

## Quick start

Create a virtual environment and install the project:

```sh
./scripts/setup_venv.sh
source .venv/bin/activate
```

Download the dictionary data:

```sh
daily-anki download-dictionary --output data/jmdict-eng.json
```

Create a card export from a word list:

```sh
daily-anki create --words-file words.txt --dictionary data/jmdict-eng.json --output exports/daily.tsv
```

Create a card export from a specific Apple Notes note:

```sh
daily-anki create --note-name "Daily Life" --dictionary data/jmdict-eng.json --output exports/daily.tsv
```

## Syncing directly to Anki

Start Anki Desktop and install the AnkiConnect add-on. Then check that the project can see it:

```sh
daily-anki anki-check
```

If the deck or note type is missing, you can create them:

```sh
daily-anki anki-setup
```

Preview what would be created without changing Anki:

```sh
daily-anki sync --note-name "Daily Life" --dictionary data/jmdict-eng.json --dry-run
```

Create the cards:

```sh
daily-anki sync --note-name "Daily Life" --dictionary data/jmdict-eng.json
```

## Notes

- The project is aimed at people who want to study vocabulary in context and turn it into flashcards.
- It is written for a personal workflow, but it is flexible enough to use with a small word list or with notes you keep in Apple Notes.
- The generated TSV can be imported into Anki using the standard import flow.

## License

The project code is licensed under the Apache License, Version 2.0. See [LICENSE](LICENSE) for the full text.

The project also uses dictionary data from JMDict Simplified, which has its own upstream licensing terms. See [NOTICE](NOTICE) and [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for attribution and compliance details.
