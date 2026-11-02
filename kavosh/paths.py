"""Locate packaged curriculum resources independent of the working directory.

Resolution order for the SQLite database (``resolve_db_path``):

1. an explicit path argument, or the ``KAVOSH_DB`` environment variable
   (built from the datasets on first use when missing);
2. ``kavosh/_data/curriculum.db`` bundled in the wheel (built at ``pip install`` /
   ``python -m build`` time by ``setup.py``);
3. a content-addressed build cached in the user cache directory, produced from the
   bundled (``kavosh/_datasets``) or in-repo (``datasets/``) JSON files.
"""

from __future__ import annotations

import hashlib
import os
import tempfile
from importlib import resources
from pathlib import Path

from kavosh import __version__

DB_FILENAME = "curriculum.db"
ENV_DB = "KAVOSH_DB"
ENV_CACHE_DIR = "KAVOSH_CACHE_DIR"

_FINGERPRINT_MODULES = ("seeder.py", "models.py", "schema.py", "rag.py")


def package_dir() -> Path:
    """Directory of the installed ``kavosh`` package."""
    return Path(str(resources.files("kavosh")))


def datasets_dir() -> Path:
    """Directory holding the curriculum JSON datasets (bundled or in-repo)."""
    bundled = package_dir() / "_datasets"
    if next(bundled.glob("grade*.json"), None) is not None:
        return bundled
    in_repo = package_dir().parent / "datasets"
    if in_repo.is_dir():
        return in_repo
    raise FileNotFoundError(
        "KavoshELT datasets not found: expected kavosh/_datasets (installed wheel) "
        "or ./datasets (source checkout)."
    )


def packaged_db_path() -> Path | None:
    """The prebuilt database shipped in the wheel, if present."""
    candidate = package_dir() / "_data" / DB_FILENAME
    return candidate if candidate.is_file() else None


def cache_dir() -> Path:
    override = os.environ.get(ENV_CACHE_DIR)
    if override:
        return Path(override).expanduser()
    if os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local")
    else:
        base = Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache")
    return base / "kavosh-elt"


def source_fingerprint(datasets: Path | None = None) -> str:
    """Hash of everything that determines the database content."""
    ds = datasets or datasets_dir()
    digest = hashlib.sha256(__version__.encode())
    for name in _FINGERPRINT_MODULES:
        module = package_dir() / name
        if module.is_file():
            digest.update(module.read_bytes())
    for path in sorted(ds.glob("*.json")):
        digest.update(path.name.encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()[:16]


def default_db_path() -> Path:
    """Where the default database lives (without building it)."""
    packaged = packaged_db_path()
    if packaged is not None:
        return packaged
    return cache_dir() / f"curriculum-{source_fingerprint()}.db"


def build_database_file(db_path: Path, datasets: Path | None = None) -> Path:
    """Build a fresh database atomically (temp file + rename)."""
    from kavosh.schema import init_db
    from kavosh.seeder import seed_curriculum

    db_path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(suffix=".tmp", dir=db_path.parent)
    os.close(fd)
    try:
        init_db(tmp_name)
        seed_curriculum(tmp_name, str(datasets or datasets_dir()))
        os.replace(tmp_name, db_path)
    except BaseException:
        Path(tmp_name).unlink(missing_ok=True)
        raise
    return db_path


def resolve_db_path(
    explicit: str | os.PathLike[str] | None = None, *, build: bool = True
) -> Path:
    """Return the database path, building it first when it does not exist."""
    chosen = explicit if explicit is not None else os.environ.get(ENV_DB)
    path = Path(chosen).expanduser() if chosen else default_db_path()
    if build and not path.exists():
        build_database_file(path)
    return path
