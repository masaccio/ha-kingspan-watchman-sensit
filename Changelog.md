# What's Changed

🪲 indicates bug fixes
🚀 indicates new features or improvements

## v1.6.5

🪲 Fixes load failure [issue-18](https://github.com/masaccio/ha-kingspan-watchman-sensit/issues/18) on newer versions of Home Assistant Core.

## v1.6.3

Minor bug fixes:

🪲 Remove 'Unsupported state class' for tank capacity ([issue-17](https://github.com/masaccio/ha-kingspan-watchman-sensit/issues/17))
🪲 Threshold for a refill changed to +10% for calculating daily usage ([issue-15](https://github.com/masaccio/ha-kingspan-watchman-sensit/issues/15))
🪲 Allow setup of the integration before any readings have been sent to Kingspan's servers ([issue-14](https://github.com/masaccio/ha-kingspan-watchman-sensit/issues/14))

## v1.6.2

🪲 Fixes load failure [issue-10](https://github.com/masaccio/ha-kingspan-watchman-sensit/issues/10) on newer versions of Home Assistant Core. The minimum version is now 2023.10.0.

## v1.6.1

🪲 Fixes error handling for Kingspan API problems [issue-9](https://github.com/masaccio/ha-kingspan-watchman-sensit/issues/9).

## v1.6.0

🚀 Configuration option added for debugging Kingspan connections. When enabled, very verbose logs are generated for the connection to the Kingspan internet service. The logs include username and password.

## v1.5.0

🚀 The integration now supports an options flow for configuring parameters. Currently supported parameters are the update interval (default is 8 hours) and the number of days to consider for average usage (default is 14 days). You can change these by clicking **Configure** from the integration's entry in **Settings > Devices & Services**.

[![Open your Home Assistant instance and show the SENSiT integration.](https://my.home-assistant.io/badges/integration.svg)](https://my.home-assistant.io/redirect/integration/?domain=kingspan_watchman_sensit)

## v1.4.5

🪲 Fixes timezone mismatch [issue-7](https://github.com/masaccio/ha-kingspan-watchman-sensit/issues/7). Previously the integration assumed that times were reported in UTC, which could result in **Last Reading Date** errors.

## v1.4.4

🪲 Fixes load failure [issue-6](https://github.com/masaccio/ha-kingspan-watchman-sensit/issues/6) on newer versions of Home Assistant Core.

## v1.4.3

🪲 Fixes load failure [issue-4](https://github.com/masaccio/ha-kingspan-watchman-sensit/issues/4) on newer versions of Home Assistant Core. The minimum version is now 2023.1.0.

## v1.4.2

🪲 Resolved `not a valid unit for the device class` warnings in Home Assistant logs.

## v1.4.1

🪲 Restored model name to device entity. Added default name for new installations.

## v1.4.0

🚀 Added support for multiple tanks.
