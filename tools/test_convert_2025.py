import convert_2025


def test_refuses_to_run_at_all_because_it_is_superseded(capsys):
    """convert_2025 reads the old website's HTML, which holds 82 of the 166
    entries in the समाज's markdown list. Running it would drop 84 donors."""
    assert convert_2025.main() == 1
    out = capsys.readouterr().out
    assert "REFUSED" in out
    assert "convert_2025_md.py" in out


def test_the_later_year_guard_still_holds(tmp_path, monkeypatch, capsys):
    """The original guard, tested on the body that main() used to run. Without
    this, the superseded refusal above would be the only thing under test and
    the later-year guard would rot unnoticed."""
    out = tmp_path / "donors-2025.json"
    (tmp_path / "donors-2026.json").write_text("{}", encoding="utf-8")
    index = tmp_path / "donors-index.json"
    index.write_text('{"years": [2025, 2026]}', encoding="utf-8")
    monkeypatch.setattr(convert_2025, "OUT", out)
    monkeypatch.setattr(convert_2025, "INDEX", index)
    assert convert_2025.main_unused() == 1
    assert "REFUSED" in capsys.readouterr().out
    assert index.read_text(encoding="utf-8") == '{"years": [2025, 2026]}'
