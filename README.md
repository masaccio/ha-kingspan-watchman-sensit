# Kingspan Watchman SENSiT integration for Home Assistant

[![build:](https://github.com/masaccio/ha-kingspan-watchman-sensit/actions/workflows/run-all-tests.yml/badge.svg)](https://github.com/masaccio/ha-kingspan-watchman-sensit/actions/workflows/run-all-tests.yml)
[![codecov](https://codecov.io/gh/masaccio/ha-kingspan-watchman-sensit/branch/main/graph/badge.svg?token=EKIUFGT05E)](https://codecov.io/gh/masaccio/ha-kingspan-watchman-sensit)
[![GitHub release](https://img.shields.io/github/release/masaccio/ha-kingspan-watchman-sensit.svg)](https://GitHub.com/masaccio/ha-kingspan-watchman-sensit/releases/)
[![HA integration usage](https://img.shields.io/badge/dynamic/json?color=41BDF5&logo=home-assistant&label=integration%20usage&suffix=%20installs&cacheSeconds=15600&url=https://analytics.home-assistant.io/custom_integrations.json&query=$.kingspan_watchman_sensit.total)]([https://analytics.home-assistant.io/custom_integrations.json](https://www.home-assistant.io))

This repository contains a Home Assistant integration for the [Kingspan Watchman SENSiT sensors](https://www.kingspan.com/gb/en-gb/products/tank-monitoring-systems/remote-tank-monitoring/sensit-smart-wifi-tank-level-monitoring-kit) to read levels from an oil tank. The integration relies upon a connection to Kingspan's cloud service.

## Installation

You will need [HACS](https://hacs.xyz) installed in your Home Assistant server. Install the Kingspan Watchman SENSiT integration and you will then be asked to enter your username and password for logging into the Kingspan server. This is then cached by Home Assistant.

You will be asked for your Kingspan username and password which will then be cached by Home Assistant for all future updates.

During installation, the following parameters are requested:

- Username: your Kingspan account email address.
- Password: your Kingspan account password.
- Tank name (optional): a friendly name used for the entity naming in Home Assistant.

[![Open your Home Assistant instance and add this integration](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=kingspan_watchman_sensit)

## Removal

To remove the integration from Home Assistant:

1. Open Settings > Devices & Services.
2. Select Kingspan Watchman SENSiT.
3. Click the three-dot menu and choose Delete.
4. Confirm the removal.

This removes the integration entry from Home Assistant. Your Kingspan account credentials are managed by Home Assistant and are not deleted automatically by the integration itself.

## Entities

The integration reads data from the SENSiT sensor every 8 hours. The tank data is updated every 24 hours but 8 hours is chosen as the update point. Usage data and forecasts of empty are different from the Kingspan app. Rather than using just the previous day's reading, this integration uses the past 14 days as the basis for a prediction of empty, and the current usage is also the average of the past 14 days. These values can be changed in the [integration's configuration](#configuration).

![Lovelace Card for SENSiT integration](https://raw.githubusercontent.com/masaccio/ha-kingspan-watchman-sensit/main/images/lovelace-card.png)

## Configuration

![Configuration options for SENSiT integration](https://raw.githubusercontent.com/masaccio/ha-kingspan-watchman-sensit/main/images/configuration.png)

You can configure some parameters for the integration using by clicking **Configure** from the integration's entry in **Settings > Devices & Services** which is available through this helper:

[![Open your Home Assistant instance and show the SENSiT integration.](https://my.home-assistant.io/badges/integration.svg)](https://my.home-assistant.io/redirect/integration/?domain=kingspan_watchman_sensit)

The integration exposes the following configuration parameters in the options flow:

- Update interval: how often to poll the Kingspan service, in hours. Default: 8.
- Usage window: the number of recent days used to calculate usage and forecast-empty values. Default: 14.
- Oil energy density: the conversion factor used for oil-to-energy calculations, in kWh per litre. Default: 9.8.
- Debug Kingspan: enables verbose debug logging for the API client when troubleshooting connectivity or parsing issues.

The tank refresh interval configures how often the integration will request new data from the Kingspan service. The SENSiT tank transmitter only updates every 2 hours, but the timing is not configurable. It is therefore possible that the integration and the Kingspan service can not be well aligned, so this option allows for more frequent checks.

The usage interval is the number of days to average for oil usage. This is also used to calculate the predicted empty date.

## Data update

The integration uses Home Assistant's config-entry polling model to fetch updated tank information from the Kingspan cloud service. By default it checks every 8 hours, but this can be adjusted in the options flow.

The underlying SENSiT transmitter updates at regular intervals, and the integration reads the latest available data from the cloud rather than from a local network device. For this reason, the displayed state reflects the most recent cloud reading rather than a direct local sensor feed.

## Supported devices

This integration is designed for Kingspan Watchman SENSiT smart tank-monitoring systems that expose data through the Kingspan cloud API for residential and commercial oil tank monitoring.

## Supported functions

The integration supports:

- reading current tank level
- reading tank capacity and percentage full
- reporting last reading timestamp
- calculating rolling usage rate and forecast empty date
- converting usage to energy figures for Energy Dashboard use
- tracking cumulative oil consumption over time

## Known limitations

- The integration is cloud-based and does not discover devices locally.
- Data availability depends on the Kingspan cloud service and connector availability.
- The forecast and usage calculations use the configured rolling history window; they are estimates based on recent readings rather than an exact tank model.
- The integration only supports a single Kingspan account per config entry and one or more tanks associated with that account.

## Troubleshooting

If the integration does not update as expected:

1. Verify the Kingspan username and password are still valid.
2. Check the Home Assistant logs for authentication or API errors.
3. Confirm the account has data available for the configured tank.
4. In the options flow, enable the debug flag to capture more detailed API logging.
5. Review the update interval and usage window settings to ensure they match your monitoring expectations.

## Use cases

This integration is intended for users who want to monitor heating oil levels and consumption, predict when a tank may run empty, and include oil use in Home Assistant energy dashboards or custom monitoring views.

## Energy Dashboard

[Home Assistant Energy Management](https://www.home-assistant.io/docs/energy/) doesn't include support for oil consumption, so you need to use gas instead. This integration provides a sensor `sensor.oil_consumption` which is the monotonically increasing amount of oil consumed represented as kWh. The sensor is restored on restart and updated every day using the `sensor.current_usage` value.

The integration uses a simple conversion of 9.8kWh per litre of oil to calculate the energy usage in kWh. This value assumes 10.35 kWh per litre for heating oil and a boiler efficiency of 95%. The value can be configured in the integration's configuration.

You can add price information by locating a suitable online price source and scraping the value. In the UK, one such source is Home Fuels Direct which is a cheap broker for oil and publishes prices by UK county. Add the following template to your `configuration.yaml`, adjusting the URL to your location and restarting Home Assistant. The scan interval in this example is set to 24 hours.

```yaml
scrape:
  - resource: https://homefuelsdirect.co.uk/home/heating-oil-prices/london
    scan_interval: 86400
    sensor:
      - name: oil_price_per_litre
        device_class: monetary
        state_class: measurement
        unit_of_measurement: "../L"
        select: "span.price"
        value_template: "{{ (value | float / 100) | round(4) }}"
```

With this, you can configure gas consumption in Home Assistant by adding `sensor.oil_consumption` as your source of gas usage, then select "Use an entity with current price" and use your new `sensor.oil_price_per_litre` sensor as the price feed.

The integration also exposes per-tank sensors such as `sensor.tanky_mctankface_oil_level`, `sensor.tanky_mctankface_current_usage`, and `sensor.tanky_mctankface_oil_consumption` to support dashboards and automations.
