"""Where ff keeps its data, and the user-editable config.toml."""

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path

DEFAULT_CONFIG = """\
# Folder names skipped entirely during indexing, matched case-insensitively wherever they occur.
exclude = ['$Recycle.Bin', 'System Volume Information', '.git']

# Folders to index. Empty means every fixed drive. Use single quotes so backslashes stay literal:
# roots = ['D:\\', 'E:\\Projects']
roots = []
"""


@dataclass(frozen=True)
class Config:
    home: Path
    exclude: list[str]
    roots: list[str]

    @property
    def index_path(self):
        return self.home / "index.db"


def home():
    override = os.environ.get("FF_HOME")
    return Path(override) if override else Path(os.environ["LOCALAPPDATA"]) / "FileSearch"


def load():
    """Read config.toml, writing the default one first if it does not exist."""
    h = home()
    path = h / "config.toml"
    if not path.exists():
        h.mkdir(parents=True, exist_ok=True)
        path.write_text(DEFAULT_CONFIG, encoding="utf-8")
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    return Config(h, list(data.get("exclude", [])), list(data.get("roots", [])))
