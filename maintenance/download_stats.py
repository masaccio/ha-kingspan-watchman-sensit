#! /usr/bin/env uv run python3

"""Extract per version download stats."""

import json
import sys
import urllib.request


def main():
    """Stats main."""
    # URL for Home Assistant's official custom integration analytics
    url = "https://analytics.home-assistant.io/custom_integrations.json"
    domain = "kingspan_watchman_sensit"

    print(f"Fetching live analytics data from {url}...")

    try:
        # Include a User-Agent header to prevent blocking by generic bot filters
        req = urllib.request.Request(
            url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        )

        with urllib.request.urlopen(req) as response:
            raw_data = response.read().decode("utf-8")
            data = json.loads(raw_data)

    except urllib.error.URLError as e:
        print(f"Network error trying to fetch analytics: {e}", file=sys.stderr)
        return
    except json.JSONDecodeError as e:
        print(f"Failed to parse the retrieved JSON data: {e}", file=sys.stderr)
        return

    # Check if the domain exists in the dataset
    if domain not in data:
        print(f"\nCould not find data for domain: '{domain}'")
        print("Note: Integrations must have a minimum threshold of opt-in installations to appear.")
        return

    integration_data = data[domain]

    # Print the core overview metrics
    print("\n" + "=" * 45)
    print(f" ANALYTICS FOR: {domain}")
    print("=" * 45)

    # Check if the analytics file provides a total count top-level key or versions
    if isinstance(integration_data, dict):
        # Home Assistant typically groups version breakdowns under 'versions' or returns it flat
        versions = integration_data.get("versions", integration_data)
        total_installations = integration_data.get("total", "N/A")

        if total_installations != "N/A":
            print(f"Total Opt-in Installations: {total_installations}\n")

        print(f"{'Version':<20} | {'Active Installations':<20}")
        print("-" * 45)

        # Filter and sort the version breakdown keys
        # Skips metadata keys if present in the dictionary block
        metadata_keys = {"total", "domain"}
        sorted_versions = sorted(
            [(k, v) for k, v in versions.items() if k not in metadata_keys],
            key=lambda x: str(x[0]),
            reverse=True,
        )

        for version, count in sorted_versions:
            print(f"{str(version):<20} | {str(count):<20}")

    elif isinstance(integration_data, int):
        # If the file format drops the dictionary nesting and only yields total installations
        print(f"Total Active Installations: {integration_data}")
        print(
            "\nNote: The global dataset only provides the cumulative "
            "installation footprint for this component."
        )


if __name__ == "__main__":
    main()
