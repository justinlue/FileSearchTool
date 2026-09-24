"""Walk drives and yield every file and folder as (path, name, is_dir)."""

import ctypes
import os
import string

LONG = "\\\\?\\"  # extended-length prefix: lifts the 260-char MAX_PATH limit
DRIVE_FIXED = 3


def fixed_drives():
    kernel32 = ctypes.windll.kernel32
    mask = kernel32.GetLogicalDrives()
    roots = [f"{letter}:\\" for i, letter in enumerate(string.ascii_uppercase) if mask >> i & 1]
    return [r for r in roots if kernel32.GetDriveTypeW(r) == DRIVE_FIXED]


def walk(roots, exclude=(), on_skip=None):
    """Depth-first walk. Excluded folder names are skipped entirely; junctions and
    symlinks are yielded but never descended into; unreadable folders go to on_skip."""
    excluded = {name.casefold() for name in exclude}
    stack = [LONG + os.path.abspath(root) for root in reversed(roots)]
    while stack:
        folder = stack.pop()
        try:
            with os.scandir(folder) as it:
                children = []
                for e in it:
                    is_link = e.is_symlink() or e.is_junction()
                    is_dir = e.is_dir(follow_symlinks=False) or e.is_junction()
                    if is_dir and e.name.casefold() in excluded:
                        continue
                    yield e.path[len(LONG):], e.name, is_dir
                    if is_dir and not is_link:
                        children.append(e.path)
        except OSError:
            if on_skip:
                on_skip(folder[len(LONG):])
            continue
        stack.extend(reversed(children))
