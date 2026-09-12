import os
import subprocess
import sys
from pathlib import Path


def test_package_imports_from_outside_repo(tmp_path):
    repo_root = Path(__file__).resolve().parents[1]
    code = """
import importlib
for module_name in [
    "config",
    "EeImageCollections",
    "FeatureManipulation",
    "Pipelines",
    "read_and_write",
    "ReducedCollections",
    "utils",
]:
    importlib.import_module(module_name)
"""

    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": str(repo_root)},
    )

    assert result.returncode == 0, result.stderr or result.stdout
