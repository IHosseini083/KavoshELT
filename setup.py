"""Build hook: bundle the curriculum datasets (and a prebuilt SQLite DB) in wheels.

``kavosh/_datasets`` and ``kavosh/_data/curriculum.db`` are generated into the build
directory so ``pip install kavosh-elt`` works from any working directory.  Editable
installs and source checkouts fall back to ``./datasets`` and a per-user cache DB
(see ``kavosh/paths.py``).
"""

from __future__ import annotations

import shutil
import sys
import warnings
from pathlib import Path

from setuptools import setup
from setuptools.command.build_py import build_py as _build_py

ROOT = Path(__file__).resolve().parent


class build_py(_build_py):
    def run(self) -> None:
        super().run()
        if getattr(self, "editable_mode", False):
            return
        pkg_out = Path(self.build_lib) / "kavosh"
        datasets_out = pkg_out / "_datasets"
        datasets_out.mkdir(parents=True, exist_ok=True)
        for source in sorted((ROOT / "datasets").glob("*.json")):
            shutil.copy2(source, datasets_out / source.name)
        self._prebuild_database(pkg_out / "_data" / "curriculum.db", datasets_out)

    @staticmethod
    def _prebuild_database(db_path: Path, datasets: Path) -> None:
        sys.path.insert(0, str(ROOT))
        try:
            from kavosh.paths import build_database_file

            build_database_file(db_path, datasets)
        except Exception as exc:  # the DB is rebuilt lazily at first use otherwise
            warnings.warn(
                f"Could not prebuild curriculum.db ({exc}); it will be built on first use."
            )
        finally:
            sys.path.remove(str(ROOT))


setup(cmdclass={"build_py": build_py})
