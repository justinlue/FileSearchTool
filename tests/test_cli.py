import sqlite3
import time

import pytest

from ff import cli


@pytest.fixture
def env(tmp_path, monkeypatch):
    """A data dir whose config indexes only a small tree, never the real drives."""
    home, tree = tmp_path / "home", tmp_path / "tree"
    home.mkdir()
    tree.mkdir()
    (tree / "docs").mkdir()
    (tree / "docs" / "report.pdf").write_text("x")
    (tree / "notes.txt").write_text("x")
    for i in range(3):
        (tree / f"log{i}.log").write_text("x")
    root = str(tree).replace("\\", "\\\\")
    (home / "config.toml").write_text(f'exclude = [".git"]\nroots = ["{root}"]\n', encoding="utf-8")
    monkeypatch.setenv("FF_HOME", str(home))
    return home, tree


def run(capsys, *argv):
    code = cli.main(list(argv))
    out, err = capsys.readouterr()
    return code, out.splitlines(), err


def test_first_search_builds_index_then_answers(env, capsys):
    home, tree = env
    code, out, err = run(capsys, "report")
    assert code == 0
    assert out == [str(tree / "docs" / "report.pdf")]
    assert "Building index" in err
    assert (home / "index.db").exists()


def test_folders_print_with_trailing_backslash(env, capsys):
    _, tree = env
    _, out, _ = run(capsys, "docs")
    assert out == [str(tree / "docs") + "\\"]


def test_truncation_notice_goes_to_stderr(env, capsys):
    _, out, err = run(capsys, ".log", "-n", "2")
    assert len(out) == 2
    assert "and 1 more" in err


def test_all_lifts_the_cap(env, capsys):
    _, out, err = run(capsys, ".log", "-n", "1", "--all")
    assert len(out) == 3
    assert "more" not in err


def test_no_match_exits_1(env, capsys):
    code, out, err = run(capsys, "zzz-nothing")
    assert code == 1
    assert out == []
    assert "No matches" in err


def test_second_search_uses_existing_index(env, capsys):
    _, tree = env
    run(capsys, "report")
    (tree / "fresh.txt").write_text("x")
    _, out, err = run(capsys, "fresh")
    assert out == []
    assert "Building index" not in err


def test_reindex_picks_up_new_files(env, capsys):
    _, tree = env
    run(capsys, "report")
    (tree / "fresh.txt").write_text("x")
    code, _, err = run(capsys, "--reindex")
    assert code == 0
    assert "Indexed" in err
    _, out, _ = run(capsys, "fresh")
    assert out == [str(tree / "fresh.txt")]


def test_reindex_reports_skipped_folders(env, capsys):
    home, tree = env
    root = str(tree).replace("\\", "\\\\")
    missing = str(tree / "gone").replace("\\", "\\\\")
    (home / "config.toml").write_text(f'roots = ["{missing}", "{root}"]\n', encoding="utf-8")
    _, _, err = run(capsys, "--reindex")
    assert "1 folder skipped" in err


def test_stale_index_warns(env, capsys):
    home, _ = env
    run(capsys, "report")
    with sqlite3.connect(home / "index.db") as con:
        con.execute("UPDATE meta SET value = ? WHERE key = 'built_at'", (time.time() - 25 * 3600,))
    _, out, err = run(capsys, "report")
    assert len(out) == 1
    assert "25 hours old" in err


def test_fresh_index_does_not_warn(env, capsys):
    run(capsys, "report")
    _, _, err = run(capsys, "report")
    assert "old" not in err


def test_live_scans_without_touching_the_index(env, capsys):
    home, tree = env
    code, out, _ = run(capsys, "--live", "report")
    assert code == 0
    assert out == [str(tree / "docs" / "report.pdf")]
    assert not (home / "index.db").exists()


def test_live_ranks_like_the_index(env, capsys):
    _, tree = env
    (tree / "docs" / "notes").mkdir()
    (tree / "docs" / "notes" / "notes.txt").write_text("x")
    (tree / "old_notes.txt").write_text("x")
    _, live, _ = run(capsys, "--live", "notes.txt")
    _, indexed, _ = run(capsys, "notes.txt")
    assert live == indexed


def test_missing_config_is_created_with_defaults(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("FF_HOME", str(tmp_path))
    from ff.config import load

    config = load()
    assert (tmp_path / "config.toml").exists()
    assert "$Recycle.Bin" in config.exclude
    assert config.roots == []


def test_copy_flag_copies_top_hit(env, capsys, monkeypatch):
    _, tree = env
    copied = []
    monkeypatch.setattr(cli.actions, "copy", copied.append)
    run(capsys, "report", "-c")
    assert copied == [str(tree / "docs" / "report.pdf")]


def test_open_flag_reveals_top_hit(env, capsys, monkeypatch):
    _, tree = env
    revealed = []
    monkeypatch.setattr(cli.actions, "reveal", revealed.append)
    run(capsys, "report", "-o")
    assert revealed == [str(tree / "docs" / "report.pdf")]


def test_query_is_required_unless_reindexing(env, capsys):
    with pytest.raises(SystemExit):
        cli.main([])


def test_piped_output_is_utf8_even_on_a_gbk_system(env, monkeypatch):
    import io
    import sys

    _, tree = env
    (tree / "报告_Übersicht.txt").write_text("x")
    raw = io.BytesIO()
    monkeypatch.setattr(sys, "stdout", io.TextIOWrapper(raw, encoding="gbk"))
    assert cli.main(["übersicht"]) == 0
    sys.stdout.flush()
    assert raw.getvalue().decode("utf-8").strip() == str(tree / "报告_Übersicht.txt")
