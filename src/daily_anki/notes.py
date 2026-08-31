import re
import subprocess


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
    text = re.sub(r"<[^>]+>", "\n", result.stdout)
    words = []
    for line in text.splitlines():
        cleaned = re.sub(r"^\s*(?:[-*•]|\[[ xX]\])\s*", "", line).strip()
        if cleaned:
            words.append(cleaned)
    return words
