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

CLEAR_NOTE_SCRIPT = r'''on run argv
    set requestedFolder to item 1 of argv
    set requestedNote to item 2 of argv
    tell application "Notes"
        repeat with currentNote in notes of default account
            if name of currentNote is requestedNote and (requestedFolder is "" or name of container of currentNote is requestedFolder) then
                set body of currentNote to ""
                return "cleared"
            end if
        end repeat
        error "Note not found: " & requestedNote
    end tell
end run'''

JAPANESE_RUN = re.compile(r"[\u3040-\u309f\u30a0-\u30ff\u3400-\u4dbf\u4e00-\u9fff々ー]+")
LIST_MARKER = re.compile(r"^\s*(?:[-*•]|\[[ xX]\])\s*")


def fetch_words(folder: str = "", note_name: str = "") -> list[str]:
    result = subprocess.run(
        ["osascript", "-e", APPLE_SCRIPT, folder, note_name],
        check=True,
        capture_output=True,
        text=True,
    )
    return parse_note_words(result.stdout)


def clear_note(folder: str, note_name: str) -> None:
    subprocess.run(
        ["osascript", "-e", CLEAR_NOTE_SCRIPT, folder, note_name],
        check=True,
        capture_output=True,
        text=True,
    )


class _NoteTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._skip_heading = False

    def handle_data(self, data: str) -> None:
        if not self._skip_heading:
            self.parts.append(data)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, Optional[str]]]) -> None:
        if tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            self._skip_heading = True
        elif tag in {"br", "div", "li", "p", "tr"}:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            self._skip_heading = False
        elif tag in {"div", "li", "p", "tr"}:
            self.parts.append("\n")


def parse_note_words(html: str) -> list[str]:
    parser = _NoteTextParser()
    parser.feed(html)
    parser.close()
    words = []
    for line in "".join(parser.parts).splitlines():
        cleaned = LIST_MARKER.sub("", line)
        words.extend(JAPANESE_RUN.findall(cleaned))
    return words
