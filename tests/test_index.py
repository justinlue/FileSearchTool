from ff.index import build, search


def entry(path, is_dir=False):
    return (path, path.rstrip("\\").rsplit("\\", 1)[-1], is_dir)


def make(tmp_path, *entries):
    db = tmp_path / "index.db"
    build(db, entries)
    return db


def paths(result):
    return [hit.path for hit in result.hits]


def test_substring_match_is_case_insensitive(tmp_path):
    db = make(tmp_path, entry(r"C:\a\Q3_Report_final.pdf"), entry(r"C:\a\notes.txt"))
    assert paths(search(db, "report")) == [r"C:\a\Q3_Report_final.pdf"]


def test_matches_name_not_directory_part_of_path(tmp_path):
    db = make(tmp_path, entry(r"C:\report\notes.txt"))
    assert paths(search(db, "report")) == []


def test_ranks_exact_then_prefix_then_contains(tmp_path):
    db = make(
        tmp_path,
        entry(r"C:\x\old_report.txt"),
        entry(r"C:\x\report.txt.bak"),
        entry(r"C:\x\deep\deeper\report.txt"),
    )
    assert paths(search(db, "report.txt")) == [
        r"C:\x\deep\deeper\report.txt",
        r"C:\x\report.txt.bak",
        r"C:\x\old_report.txt",
    ]


def test_ties_go_to_shorter_path(tmp_path):
    db = make(tmp_path, entry(r"C:\long\folder\a.txt"), entry(r"C:\s\a.txt"))
    assert paths(search(db, "a.txt")) == [r"C:\s\a.txt", r"C:\long\folder\a.txt"]


def test_star_and_question_mark_switch_to_wildcards(tmp_path):
    db = make(
        tmp_path,
        entry(r"C:\a\rep_2026_q1.pdf"),
        entry(r"C:\a\rep_2025.pdf"),
        entry(r"C:\a\my_rep_2026.pdf"),
    )
    assert paths(search(db, "rep*2026*.pdf")) == [r"C:\a\rep_2026_q1.pdf"]
    assert paths(search(db, "rep_202?.pdf")) == [r"C:\a\rep_2025.pdf"]


def test_sql_like_characters_in_query_are_literal(tmp_path):
    db = make(tmp_path, entry(r"C:\a\100%_done.txt"), entry(r"C:\a\100x_done.txt"))
    assert paths(search(db, "100%_")) == [r"C:\a\100%_done.txt"]
    assert paths(search(db, "100%_*")) == [r"C:\a\100%_done.txt"]


def test_limit_caps_hits_but_total_counts_all(tmp_path):
    db = make(tmp_path, *(entry(rf"C:\a\f{i}.log") for i in range(5)))
    result = search(db, ".log", limit=2)
    assert len(result.hits) == 2
    assert result.total == 5


def test_limit_none_returns_everything(tmp_path):
    db = make(tmp_path, *(entry(rf"C:\a\f{i}.log") for i in range(5)))
    assert len(search(db, ".log", limit=None).hits) == 5


def test_folders_are_flagged(tmp_path):
    db = make(tmp_path, entry(r"C:\a\reports", is_dir=True))
    assert search(db, "reports").hits[0].is_dir is True


def test_non_ascii_names_match_case_insensitively(tmp_path):
    db = make(tmp_path, entry(r"C:\a\ÜBERSICHT.docx"), entry(r"C:\a\报告.pdf"))
    assert paths(search(db, "übersicht")) == [r"C:\a\ÜBERSICHT.docx"]
    assert paths(search(db, "报告")) == [r"C:\a\报告.pdf"]


def test_rebuild_replaces_previous_contents(tmp_path):
    db = make(tmp_path, entry(r"C:\a\old.txt"))
    build(db, [entry(r"C:\a\new.txt")])
    assert paths(search(db, ".txt")) == [r"C:\a\new.txt"]


def test_build_records_when_it_was_built(tmp_path):
    from ff.index import built_at

    db = make(tmp_path, entry(r"C:\a\x.txt"))
    assert built_at(db) is not None
    assert built_at(tmp_path / "missing.db") is None


NAMES = ["Report.pdf", "old_report.txt", "100%_done.txt", "a[1].txt", "ÜBERSICHT.docx", "rep_2026_q1.pdf", "x"]
QUERIES = ["report", "REP*", "*.pdf", "100%_", "a[1]", "a[1]*", "übersicht", "rep_202?_*", "?", "zzz"]


def test_live_matcher_agrees_with_index_search(tmp_path):
    from ff.index import matches

    db = make(tmp_path, *(entry(r"C:\d" + "\\" + n) for n in NAMES))
    for q in QUERIES:
        via_index = {p.rsplit("\\", 1)[-1] for p in paths(search(db, q, limit=None))}
        via_matcher = {n for n in NAMES if matches(q, n)}
        assert via_matcher == via_index, q
