import subprocess
import sys
from pathlib import Path


def test_project_type_check():
    """Ensure project code passes the configured mypy check."""
    project_root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "mypy",
            "custom_components/kingspan_watchman_sensit",
            "--config-file",
            str(project_root / "pyproject.toml"),
        ],
        cwd=project_root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_project_lint_check():
    """Ensure project code passes the configured lint check."""
    project_root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pylint",
            "custom_components/kingspan_watchman_sensit",
            "--rcfile",
            str(project_root / "pyproject.toml"),
        ],
        cwd=project_root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
