import re
import subprocess
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Optional

APPLE_SCRIPT = r"""on run argv
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
end run"""

CLEAR_NOTE_SCRIPT = r"""on run argv
    set requestedFolder to item 1 of argv
    set requestedNote to item 2 of argv
    tell application "Notes"
        repeat with currentNote in notes of default account
            if name of currentNote is requestedNote and (requestedFolder is "" or name of container of currentNote is requestedFolder) then
                set noteTitle to name of currentNote
                set body of currentNote to "<div><h1>" & noteTitle & "</h1></div>"
                return "cleared"
            end if
        end repeat
        error "Note not found: " & requestedNote
    end tell
end run"""

READ_NOTE_BODY_SCRIPT = r"""on run argv
    set requestedFolder to item 1 of argv
    set requestedNote to item 2 of argv
    tell application "Notes"
        repeat with currentNote in notes of default account
            if name of currentNote is requestedNote and (requestedFolder is "" or name of container of currentNote is requestedFolder) then
                return body of currentNote
            end if
        end repeat
        error "Note not found: " & requestedNote
    end tell
end run"""

SET_NOTE_BODY_SCRIPT = r"""on run argv
    set requestedFolder to item 1 of argv
    set requestedNote to item 2 of argv
    set updatedBody to item 3 of argv
    tell application "Notes"
        repeat with currentNote in notes of default account
            if name of currentNote is requestedNote and (requestedFolder is "" or name of container of currentNote is requestedFolder) then
                set body of currentNote to updatedBody
                return "updated"
            end if
        end repeat
        error "Note not found: " & requestedNote
    end tell
end run"""

JAPANESE_RUN = re.compile(r"[\u3040-\u309f\u30a0-\u30ff\u3400-\u4dbf\u4e00-\u9fff々ー]+")
LIST_MARKER = re.compile(r"^\s*(?:[-*•]|\[[ xX]\])\s*")
LIST_ITEM_MARKER = re.compile(r"^\s*(?:[-*•]|\[[ xX]\])\s+")
REMOVABLE_BLOCK_TAGS = {"div", "li", "p", "tr"}


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


def remove_words(folder: str, note_name: str, words: list[str]) -> None:
    if not words:
        return
    result = subprocess.run(
        ["osascript", "-e", READ_NOTE_BODY_SCRIPT, folder, note_name],
        check=True,
        capture_output=True,
        text=True,
    )
    updated_body = remove_words_from_html(result.stdout.removesuffix("\n"), words)
    if updated_body == result.stdout.removesuffix("\n"):
        return
    subprocess.run(
        ["osascript", "-e", SET_NOTE_BODY_SCRIPT, folder, note_name, updated_body],
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
        elif tag in {"br", "div", "li", "p", "tr", "td", "th"}:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            self._skip_heading = False
        elif tag in {"div", "li", "p", "tr", "td", "th"}:
            self.parts.append("\n")


class _TextContentParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


@dataclass
class _HtmlBlock:
    tag: str
    start: int
    end: Optional[int] = None
    parent: Optional["_HtmlBlock"] = None
    contains_link: bool = False


class _BlockParser(HTMLParser):
    """Find source ranges for complete, list-like HTML blocks without rewriting the rest."""

    def __init__(self, html: str) -> None:
        super().__init__(convert_charrefs=True)
        self._html = html
        self._line_starts = [0]
        self._line_starts.extend(
            index + 1 for index, character in enumerate(html) if character == "\n"
        )
        self._open_tags: list[_HtmlBlock] = []
        self.blocks: list[_HtmlBlock] = []

    def _offset(self) -> int:
        line, column = self.getpos()
        return self._line_starts[line - 1] + column

    def handle_starttag(self, tag: str, attrs: list[tuple[str, Optional[str]]]) -> None:
        if tag == "a":
            for block in self._open_tags:
                block.contains_link = True
        if tag not in REMOVABLE_BLOCK_TAGS:
            return
        parent = next(
            (block for block in reversed(self._open_tags) if block.tag in REMOVABLE_BLOCK_TAGS),
            None,
        )
        block = _HtmlBlock(tag=tag, start=self._offset(), parent=parent)
        self._open_tags.append(block)

    def handle_endtag(self, tag: str) -> None:
        for index in range(len(self._open_tags) - 1, -1, -1):
            block = self._open_tags[index]
            if block.tag != tag:
                continue
            end = self._html.find(">", self._offset())
            if end != -1:
                block.end = end + 1
                self.blocks.append(block)
            del self._open_tags[index:]
            return


def remove_words_from_html(html: str, words: list[str]) -> str:
    """Remove only complete vocabulary-list blocks, never arbitrary word substrings.

    A block is removable when it contains exactly one requested Japanese word and is
    either a list item, a marked list line, or a bare word line. Blocks containing
    links are deliberately retained so URLs and reference material cannot be damaged.
    """
    requested_words = {word.strip() for word in words if word.strip()}
    if not requested_words:
        return html

    parser = _BlockParser(html)
    parser.feed(html)
    parser.close()
    removable: list[_HtmlBlock] = []
    for block in parser.blocks:
        if block.end is None or block.contains_link:
            continue
        block_html = html[block.start : block.end]
        parsed_words = parse_note_words(block_html)
        if len(parsed_words) != 1 or parsed_words[0] not in requested_words:
            continue
        visible_text = _visible_text(block_html).strip()
        if (
            block.tag == "li"
            or visible_text == parsed_words[0]
            or LIST_ITEM_MARKER.match(visible_text)
        ):
            removable.append(block)

    ranges = _outermost_ranges(removable)
    return "".join(
        part for index, part in enumerate(_split_html_at_ranges(html, ranges)) if index % 2 == 0
    )


def _visible_text(html: str) -> str:
    parser = _TextContentParser()
    parser.feed(html)
    parser.close()
    return "".join(parser.parts)


def _outermost_ranges(blocks: list[_HtmlBlock]) -> list[tuple[int, int]]:
    ranges = []
    for block in sorted(blocks, key=lambda candidate: (candidate.start, -(candidate.end or 0))):
        if not any(start <= block.start and (block.end or 0) <= end for start, end in ranges):
            ranges.append((block.start, block.end or block.start))
    return ranges


def _split_html_at_ranges(html: str, ranges: list[tuple[int, int]]) -> list[str]:
    parts = []
    cursor = 0
    for start, end in ranges:
        parts.extend((html[cursor:start], html[start:end]))
        cursor = end
    parts.append(html[cursor:])
    return parts


def parse_note_words(html: str) -> list[str]:
    parser = _NoteTextParser()
    parser.feed(html)
    parser.close()
    words = []
    for line in "".join(parser.parts).splitlines():
        cleaned = LIST_MARKER.sub("", line)
        words.extend(JAPANESE_RUN.findall(cleaned))
    return words
