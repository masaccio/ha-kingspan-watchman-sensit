#! /usr/bin/env poetry run python3
from connectsensor import __version__ as API_VERSON
import json
import toml

MANIFEST = "custom_components/kingspan_watchman_sensit/manifest.json"

pyproject = toml.load("pyproject.toml")

manifest = {
    "domain": "kingspan_watchman_sensit",
    "name": "Kingspan Watchman SENSiT",
    "documentation": "https://github.com/masaccio/ha-kingspan-watchman-sensit",
    "iot_class": "cloud_polling",
    "issue_tracker": "https://github.com/masaccio/ha-kingspan-watchman-sensit/issues",
    "version": pyproject["tool"]["poetry"]["version"],
    "config_flow": True,
    "codeowners": ["@masaccio"],
    "requirements": [f"kingspan-connect-sensor=={API_VERSON}"],
}

with open(MANIFEST, "w") as fh:
    json.dump(manifest, fh, indent=2)
