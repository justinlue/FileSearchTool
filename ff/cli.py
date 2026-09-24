"""ff: find files by name across every fixed drive."""

import argparse
import sys
import tempfile
import time
from pathlib import Path

from ff import actions, index
from ff.config import load
from ff.walk import fixed_drives, walk

STALE_HOURS = 24


def err(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


def parse(argv):
    p = argparse.ArgumentParser(prog="ff", description=__doc__)
    p.add_argument("query", nargs="?", help="part of a file name, or a pattern with * and ?")
    p.add_argument("-n", type=int, default=50, metavar="N", help="show at most N results (default 50)")
    p.add_argument("--all", action="store_true", help="show every result")
    p.add_argument("-c", "--copy", action="store_true", help="copy the top result's path to the clipboard")
    p.add_argument("-o", "--open", action="store_true", help="open the top result's folder in Explorer")
    p.add_argument("--live", action="store_true", help="scan the drives now instead of using the index")
    p.add_argument("--reindex", action="store_true", help="rebuild the index")
    args = p.parse_args(argv)
    if args.query is None and not args.reindex:
        p.error("a query is required (or use --reindex)")
    return args


def reindex(config):
    skipped = []

    def progress(count):
        err(f"\r  {count:,} entries...", end="", flush=True)

    roots = config.roots or fixed_drives()
    err(f"Building index of {', '.join(roots)}")
    start = time.monotonic()
    entries = walk(roots, config.exclude, on_skip=skipped.append)
    count = index.build(config.index_path, entries, on_progress=progress)
    s = "" if len(skipped) == 1 else "s"
    err(f"\rIndexed {count:,} entries in {time.monotonic() - start:.0f}s; "
        f"{len(skipped):,} folder{s} skipped (access denied or unreadable).")


def live_search(config, query, limit):
    """Scan now, keep only matching names, and rank them with the same SQL as the index."""
    err("Scanning drives...")
    entries = walk(config.roots or fixed_drives(), config.exclude)
    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "live.db"
        index.build(db, (e for e in entries if index.matches(query, e[1])))
        return index.search(db, query, limit)


def main(argv=None):
    args = parse(sys.argv[1:] if argv is None else argv)
    config = load()
    # Piped stdout defaults to the ANSI code page (e.g. GBK), which cannot hold every
    # file name. UTF-8 can.
    sys.stdout.reconfigure(encoding="utf-8")

    if args.reindex:
        reindex(config)
        if args.query is None:
            return 0

    limit = None if args.all else args.n
    if args.live:
        result = live_search(config, args.query, limit)
    else:
        built = index.built_at(config.index_path)
        if built is None:
            reindex(config)
        elif (age := (time.time() - built) / 3600) > STALE_HOURS:
            err(f"Index is {age:.0f} hours old; run 'ff --reindex' to refresh it.")
        result = index.search(config.index_path, args.query, limit)

    if not result.hits:
        err(f"No matches for '{args.query}'.")
        return 1
    for hit in result.hits:
        print(hit.path + ("\\" if hit.is_dir else ""))
    if result.total > len(result.hits):
        err(f"...and {result.total - len(result.hits):,} more (use -n or --all).")

    top = result.hits[0].path
    if args.copy:
        actions.copy(top)
    if args.open:
        actions.reveal(top)
    return 0


if __name__ == "__main__":
    sys.exit(main())
