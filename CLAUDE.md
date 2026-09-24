# CLAUDE.md

`ff`: a Windows CLI that finds files by name across all fixed drives via a SQLite index. Usage is in `README.md`.

## Commands

- `python -m pytest` — full suite; tests never touch real drives or the real index.
- `pip install -e .` — installs the `ff` command (already done on this machine).

## Layout

- `ff/walk.py` — drive enumeration and the directory walker (`\\?\` long paths, no junction/symlink descent, excluded names, `on_skip` for unreadable folders).
- `ff/index.py` — `build()` writes to `index.db.tmp` then swaps it in; `search()` is the ranking SQL; `matches()` is the Python twin of the SQL filter, used by `--live`.
- `ff/config.py` — `FF_HOME` overrides the data dir (`%LOCALAPPDATA%\FileSearch`); tests rely on this plus `roots` in config.toml.
- `ff/cli.py` — argument parsing and output; `ff/actions.py` — clipboard and Explorer, monkeypatched in tests.

## Invariants

- `matches()` must agree with `search()`'s WHERE clause; `test_live_matcher_agrees_with_index_search` enforces it. Change both together.
- stdout carries only result paths. Everything else goes to stderr.
