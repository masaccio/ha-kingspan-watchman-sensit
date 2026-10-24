#! /usr/bin/env uv run python3
"""Copy integration to local hass server for testing."""

import argparse
import posixpath
import re
from io import StringIO
from pathlib import Path

from fabric import Connection

# Configuration
REMOTE_HOST = "hass"
INTEGRATION_SRC_DIR = Path("custom_components/kingspan_watchman_sensit")
DEV_SWITCHES = Path("maintenance/dev_switch.py")
REMOTE_INTEGRATION_DIR = "/config/custom_components/kingspan_watchman_sensit"
API_SRC_DIR = Path("../kingspan-connect-sensor/src/connectsensor")

# ANSI Colors
GREEN = "\033[32m"
RED = "\033[31m"
RESET = "\033[0m"


def make_dir(conn: Connection, remote_dir: str):
    """Creates a new directory on the target system."""
    conn.run(f'mkdir -p "{remote_dir}"', hide=True)


def rm_dir(conn: Connection, remote_dir: str):
    """Deletes a directory on the target system."""
    print(f"{GREEN}Remove:{RESET} {remote_dir}{GREEN}")
    conn.run(f'rm -rf "{remote_dir}"', hide=True)


def insert_local_connectsensor(content: str) -> str:
    """Patches the import paths to find the connectsensor API locally."""
    block = (
        "\nimport sys\n"
        "from pathlib import Path\n"
        "sys.path.insert(0, str(Path(__file__).resolve().parent))\n"
    )
    lines = content.splitlines(keepends=True)
    out = []
    inserted = False
    for line in lines:
        if not inserted and line.startswith("from connectsensor"):
            out.append(block + "\n")
            inserted = True
        out.append(line)
    return "".join(out)


def patch_const_for_switches(content: str) -> str:
    """Injects Platform.SWITCH into the PLATFORMS list safely."""
    if "Platform.SWITCH" not in content:
        content = re.sub(
            r"(PLATFORMS:\s*list\[Platform\]\s*=\s*\[)([^\]]*)(\])",
            lambda m: f"{m.group(1)}{m.group(2).rstrip().rstrip(',')}, Platform.SWITCH{m.group(3)}",
            content,
            flags=re.DOTALL,
        )
    return content


def copy_file(
    conn: Connection,
    src: Path,
    remote_dir: str,
    content_override: str | None = None,
    rename: str | None = None,
):
    """Copies a local file to the remote HASS server with optional patching."""
    dest_dir = remote_dir.rstrip("/")
    file_name = rename if rename else src.name
    dest_file = posixpath.join(dest_dir, file_name)

    if content_override is not None:
        print(f"{GREEN}Patch:{RESET} {src.name} {GREEN}->{RESET} {dest_file}")
        conn.put(StringIO(content_override), remote=dest_file)
    elif src.name == "manifest.json":
        print(f"{GREEN}Patch:{RESET} manifest.json {GREEN}->{RESET} {dest_file}")
        content = src.read_text(encoding="utf-8")
        patched = re.sub(r'"version":\s*".*?"', '"version": "0.0.1"', content)
        conn.put(StringIO(patched), remote=dest_file)
    else:
        print(f"{GREEN}Copy:{RESET} {src} {GREEN}->{RESET} {REMOTE_HOST}:{dest_file}")
        conn.put(str(src), remote=dest_file)


def main():
    """Script to copy the integration to a local server."""
    parser = argparse.ArgumentParser(description="Deploy Kingspan Watchman integration.")
    parser.add_argument(
        "--api", action="store_true", dest="use_local_api", help="Deploy local connectsensor API"
    )
    parser.add_argument(
        "--restart", action="store_true", dest="restart_hass", help="Restart Home Assistant Core"
    )
    parser.add_argument(
        "--mock-errors",
        action="store_true",
        dest="mock_errors",
        help="Deploy hidden UI switches to monkey-patch API exceptions",
    )

    args, _ = parser.parse_known_args()

    with Connection(REMOTE_HOST) as conn:
        rm_dir(conn, REMOTE_INTEGRATION_DIR)
        integration_files = sorted(INTEGRATION_SRC_DIR.glob("*.py"))
        integration_files.extend(sorted(INTEGRATION_SRC_DIR.glob("**/*.json")))
        integration_files.extend(sorted(INTEGRATION_SRC_DIR.glob("**/*.png")))

        for src_file in integration_files:
            content_override = None

            if args.use_local_api and src_file.name == "api.py":
                content = src_file.read_text(encoding="utf-8")
                content_override = insert_local_connectsensor(content)

            if args.mock_errors and src_file.name == "const.py":
                content = src_file.read_text(encoding="utf-8")
                content_override = patch_const_for_switches(content)

            sub_dir = src_file.relative_to(INTEGRATION_SRC_DIR).parent
            target_dir = REMOTE_INTEGRATION_DIR / sub_dir
            make_dir(conn, str(target_dir))
            copy_file(conn, src_file, str(target_dir), content_override)

        if args.mock_errors:
            copy_file(conn, DEV_SWITCHES, str(REMOTE_INTEGRATION_DIR), rename="switch.py")

        # API, Translations, Brand logic remains identical...
        remote_api_dir = posixpath.join(REMOTE_INTEGRATION_DIR, "connectsensor")
        if not args.use_local_api:
            conn.run(f'rm -rf "{remote_api_dir}"', hide=True)
        else:
            make_dir(conn, remote_api_dir)
            for src_file in sorted(API_SRC_DIR.glob("*.py")):
                copy_file(conn, src_file, remote_api_dir)

        if args.restart_hass:
            print(f"{GREEN}Restarting HA Core{RESET}")
            conn.run("source /etc/profile.d/homeassistant.sh && ha core restart")
            print(f"{GREEN}Done{RESET}")


if __name__ == "__main__":
    main()
