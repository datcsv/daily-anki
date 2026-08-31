#!/usr/bin/env sh
set -eu

PROJECT_DIR="/Users/nick/daily-anki"
VENV_DIR="$PROJECT_DIR/.venv"
DICTIONARY="$PROJECT_DIR/data/jmdict-eng.json"
HISTORY="$PROJECT_DIR/data/sync-history.jsonl"
DAILY_ANKI="$VENV_DIR/bin/daily-anki"

cd "$PROJECT_DIR"

if [ ! -x "$DAILY_ANKI" ]; then
    printf '%s\n' "Setting up the Python environment..."
    ./scripts/setup_venv.sh
fi

printf '%s\n' "Opening Anki..."
open -a Anki

printf '%s\n' "Waiting for AnkiConnect..."
sleep 5

printf '%s\n' "Updating the English JMDict dataset with examples..."
"$DAILY_ANKI" download-dictionary --output "$DICTIONARY"

printf '%s\n' "Checking AnkiConnect..."
"$DAILY_ANKI" anki-check

printf '%s\n' "Creating missing Anki resources if needed..."
"$DAILY_ANKI" anki-setup

printf '%s\n' "Syncing Daily Life and clearing processed note content..."
"$DAILY_ANKI" sync \
    --note-name "Daily Life" \
    --dictionary "$DICTIONARY" \
    --history "$HISTORY" \
    --clear-note

printf '%s\n' "Closing Anki..."

if ! osascript -e 'tell application "Anki" to quit' >/dev/null 2>&1; then
    printf '%s\n' "Anki is syncing before closing."
fi

printf '%s\n' "Morning sync complete."