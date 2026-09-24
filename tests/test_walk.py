import _winapi
import os

from ff.walk import walk


def run(roots, exclude=()):
    skipped = []
    entries = list(walk(roots, exclude, on_skip=skipped.append))
    return {(p, is_dir) for p, _, is_dir in entries}, entries, skipped


def test_yields_files_and_folders_recursively(tmp_path):
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "a.txt").write_text("x")
    (tmp_path / "b.txt").write_text("x")
    found, _, _ = run([str(tmp_path)])
    assert found == {
        (str(tmp_path / "sub"), True),
        (str(tmp_path / "sub" / "a.txt"), False),
        (str(tmp_path / "b.txt"), False),
    }


def test_yields_the_bare_name(tmp_path):
    (tmp_path / "Report.PDF").write_text("x")
    _, entries, _ = run([str(tmp_path)])
    assert entries == [(str(tmp_path / "Report.PDF"), "Report.PDF", False)]


def test_excluded_folder_names_are_skipped_case_insensitively(tmp_path):
    (tmp_path / ".GIT").mkdir()
    (tmp_path / ".GIT" / "HEAD").write_text("x")
    (tmp_path / "keep.txt").write_text("x")
    found, _, _ = run([str(tmp_path)], exclude=[".git"])
    assert found == {(str(tmp_path / "keep.txt"), False)}


def test_junctions_are_recorded_but_not_followed(tmp_path):
    target = tmp_path / "target"
    target.mkdir()
    (target / "inside.txt").write_text("x")
    _winapi.CreateJunction(str(target), str(tmp_path / "link"))
    found, _, _ = run([str(tmp_path)])
    assert (str(tmp_path / "link"), True) in found
    assert not any(p.startswith(str(tmp_path / "link") + "\\") for p, _ in found)


def test_paths_beyond_260_characters_are_found_without_prefix(tmp_path):
    deep = "\\\\?\\" + str(tmp_path)
    for _ in range(12):
        deep += "\\" + "d" * 25
        os.mkdir(deep)
    with open(deep + "\\deep.txt", "w") as f:
        f.write("x")
    _, entries, _ = run([str(tmp_path)])
    deep_file = [p for p, name, _ in entries if name == "deep.txt"]
    assert len(deep_file) == 1
    assert len(deep_file[0]) > 260
    assert not deep_file[0].startswith("\\\\?\\")


def test_unreadable_folders_are_reported_and_walk_continues(tmp_path):
    (tmp_path / "ok.txt").write_text("x")
    missing = str(tmp_path / "gone")
    found, _, skipped = run([missing, str(tmp_path)])
    assert skipped == [missing]
    assert (str(tmp_path / "ok.txt"), False) in found


def test_root_with_trailing_separator_like_a_drive_joins_cleanly(tmp_path):
    (tmp_path / "a.txt").write_text("x")
    _, entries, _ = run([str(tmp_path) + "\\"])
    assert entries[0][0] == str(tmp_path / "a.txt")


def test_fixed_drives_lists_c_drive_as_a_root():
    from ff.walk import fixed_drives

    assert "C:\\" in fixed_drives()
