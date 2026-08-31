import re
import subprocess
from html.parser import HTMLParser
from typing import Optional


APPLE_SCRIPT = r'''on run argv
    set requestedFolder to item 1 of argv
    set requestedNote to item 2 of argv
    tell application "Notes"
        set output to ""
        repeat with currentNote in notes of default account
            if requestedNote is "" or name of currentNote is requestedNote then
                if requestedFolder is "" or name of container of currentNote is requestedFolder then
                    set output to output & (body of currentNote) & return
                end if
            end if
        end repeat
        return output
    end tell
end run'''


def fetch_words(folder: str = "", note_name: str = "") -> list[str]:
    result = subprocess.run(
        ["osascript", "-e", APPLE_SCRIPT, folder, note_name],
        check=True,
        capture_output=True,
        text=True,
    )
    return parse_note_words(result.stdout)


class _NoteTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, Optional[str]]]) -> None:
        if tag in {"br", "div", "li", "p", "tr"}:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"div", "li", "p", "tr"}:
            self.parts.append("\n")


def parse_note_words(html: str) -> list[str]:
    parser = _NoteTextParser()
    parser.feed(html)
    words = []
    for line in "".join(parser.parts).splitlines():
        cleaned = re.sub(r"^\s*(?:[-*•]|\[[ xX]\])\s*", "", line).strip()
        if cleaned:
            words.append(cleaned)
    return words
