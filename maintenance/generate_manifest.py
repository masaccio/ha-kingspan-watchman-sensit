#! /usr/bin/env poetry run python3
import json
from importlib.metadata import version

import toml
from connectsensor import __version__ as connectsensor_version

MANIFEST = "custom_components/kingspan_watchman_sensit/manifest.json"

pyproject = toml.load("pyproject.toml")

httpx_version = version("httpx")

manifest = {
    "domain": "kingspan_watchman_sensit",
    "name": "Kingspan Watchman SENSiT",
    "codeowners": ["@masaccio"],
    "config_flow": True,
    "documentation": "https://github.com/masaccio/ha-kingspan-watchman-sensit",
    "iot_class": "cloud_polling",
    "issue_tracker": "https://github.com/masaccio/ha-kingspan-watchman-sensit/issues",
    "requirements": [
        f"kingspan-connect-sensor>={connectsensor_version}",
        f"httpx>={httpx_version}",
    ],
    "version": pyproject["tool"]["poetry"]["version"],
}

with open(MANIFEST, "w") as fh:
    json.dump(manifest, fh, indent=2)
