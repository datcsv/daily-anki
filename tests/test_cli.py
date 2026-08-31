import sys

import pytest

from daily_anki import cli


def test_main_reports_operational_errors_without_traceback(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["daily-anki", "download-dictionary"])
    monkeypatch.setattr(cli, "download_latest", lambda path: (_ for _ in ()).throw(RuntimeError("download failed")))

    with pytest.raises(SystemExit) as error:
        cli.main()

    assert error.value.code == 1
    assert capsys.readouterr().err == "error: download failed\n"