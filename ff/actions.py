"""Things to do with a found path beyond printing it."""

import subprocess


def copy(text):
    # clip.exe reads stdin as the OEM code page unless it sees a UTF-16 BOM.
    subprocess.run(["clip"], input=("﻿" + text).encode("utf-16-le"), check=True)


def reveal(path):
    # Explorer wants /select,"path" as one raw argument; its exit code is always 1.
    subprocess.run(f'explorer /select,"{path}"')
