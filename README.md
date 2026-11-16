# ff — find file

Find files and folders by name across every fixed drive, from a SQLite index.

```
ff report              # names containing "report", any case
ff "rep*2026*.pdf"     # * and ? switch to wildcard matching
ff report -c           # also copy the top result's path to the clipboard
ff report -o           # also open its folder in Explorer, file selected
ff .log -n 200         # show up to 200 results (default 50); --all for no cap
ff report --live       # skip the index and scan the drives now (slow, always current)
ff --reindex           # rebuild the index
```

Results print one path per line, grouped by drive letter from A to Z. Within each
drive, exact names come first, then names starting with the query, then names
containing it; ties go to the shorter path. The result limit applies after sorting.
Folders end in `\`.
Notices (truncation, stale index, progress) go to stderr, so piping stays clean.
Exit code is 1 when nothing matches.

## Index

- Lives in `%LOCALAPPDATA%\FileSearch\index.db` and is built automatically on the first search.
- Searches warn once it is more than 24 hours old. It never refreshes on its own.
- Junctions and symlinks are listed but not followed; unreadable folders are skipped and counted.

To refresh it nightly at 03:00:

```
schtasks /Create /SC DAILY /ST 03:00 /TN "ff reindex" /TR "cmd /c ff --reindex"
```

## Config

`%LOCALAPPDATA%\FileSearch\config.toml`, created with defaults on first run:

```toml
exclude = ['$Recycle.Bin', 'System Volume Information', '.git']  # folder names, any depth
roots = []                                                        # empty = every fixed drive
```

## Development

```
pip install -e .
python -m pytest
```
