# What's Changed

🪲 indicates bug fixes
🚀 indicates new features or improvements

## v2.0.2

🪲 Fixed API tokens [issue-80](https://github.com/masaccio/ha-kingspan-watchman-sensit/issues/80) with latest API library.

## v2.0.1

🪲 Fixed translations [issue-67](https://github.com/masaccio/ha-kingspan-watchman-sensit/issues/67) which caused errors in Home Assistant.

## v2.0.0

**The underlying APIs have changed significantly, so this may be an unstable release.**

This is a major update to reflect the API changes introduced by the move to KNECT Pro in February 2026. The underlying API module should be considered experimental as the roll-out of KNECT Pro was sudden and some of the APIs have a very preliminary feel so could easily change in the future. There is no date for when the APIs used by the 1.x Home Assistant integration will be retired, so you may wish to stay on that version. There are no functional differences in the 2.x versions.

🚀 Enabled dependabot to ensure that dependencies are kept up-to-date.
🚀 Multiple stability improvements in API usage.
🚀 Entity names for new integration installations are correctly scoped by tank name (does not affect existing installations).


## v1.7.0

**This version contains breaking changes to the `sensor.oil_consumption` entity.**

🪲 Fixed re-auth flow [issue-46](https://github.com/masaccio/ha-kingspan-watchman-sensit/issues/46) which caused problems re-authenticating with the Kingspan service.
🪲 Fixed `load_verify_locations` [issue-43](https://github.com/masaccio/ha-kingspan-watchman-sensit/issues/43) which had Home Assistant blocking on startup to load OpenSSL.
🪲 Fixed the spelling of the empty forecast sensor. It has been renamed to `sensor.forecast_empty`.
🚀 Updated naming of the Device Info to be more consistent with other integrations.
🚀 The oil consumption sensor `sensor.oil_consumption` has been changed to a monotonically increasing value which implements much of what is currently documented in [issue-31](https://github.com/masaccio/ha-kingspan-watchman-sensit/issues/31). The sensor assumes a fixed oil energy density in kWh per litre. This is configurable using the options configuration of the integration, and defaults to 9.8 kWh per litre. This value assumes 10.35 kWh per litre for heating oil and a boiler efficiency of 95%. The readme has been updated with installation instructions including how to fetch oil prices in the UK.
🚀 A new sensor `sensor.current_energy_usage` is a simple kWh conversion of the daily oil usage report by Kingspan. It uses the same energy density conversion factor as `sensor.oil_consumption`.
🚀 A German translation of the integration has been added. Corrections are welcomed.
