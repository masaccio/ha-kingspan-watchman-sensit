# Kingspan Watchman SENSiT integration for Home Assistant

[![build:](https://github.com/masaccio/ha-kingspan-watchman-sensit/actions/workflows/run-all-tests.yml/badge.svg)](https://github.com/masaccio/ha-kingspan-watchman-sensit/actions/workflows/run-all-tests.yml)
[![build:](https://github.com/masaccio/ha-kingspan-watchman-sensit/actions/workflows/codeql.yml/badge.svg)](https://github.com/masaccio/ha-kingspan-watchman-sensit/actions/workflows/codeql.yml)
[![codecov](https://codecov.io/gh/masaccio/ha-kingspan-watchman-sensit/branch/main/graph/badge.svg?token=EKIUFGT05E)](https://codecov.io/gh/masaccio/ha-kingspan-watchman-sensit)

This repository contains a Home Assistant integration for the [Kingspan Watchman SENSiT sensors](https://www.kingspan.com/gb/en-gb/products/tank-monitoring-systems/remote-tank-monitoring/sensit-smart-wifi-tank-level-monitoring-kit) to read levels from an oil tank. The integration relies upon a connection to Kingspan's cloud service.

## Installation

You will need [HACS](https://hacs.xyz) installed in your Home Assistant server. Install the Kingspan Watchman SENSiT integration and you will then be asked to enter your username and password for logging into the Kingspan server. This is then cached by Home Assistant.

You will be asked for your Kingspan username and password which will then be cached by Home Assistant for all future updates.

[![Open your Home Assistant instance and add this integration](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=kingspan_watchman_sensit)

## Entities

The integration reads data from the SENSiT sensor every 8 hours. The tank data is updated every 24 hours but 8 hours is chosen as the update point. Usage data and forecasts of empty are different from the Kingspan app. Rather than using just the previous day's reading, this integration uses the past 14 days as the basis for a prediction of empty, and the current usage is also the average of the past 14 days. These values can be changed in the [integration's configuration](#configuration).

![Lovelace Card for SENSiT integration](https://raw.githubusercontent.com/masaccio/ha-kingspan-watchman-sensit/main/images/lovelace-card.png)

## Configuration

![Configuration options for SENSiT integration](https://raw.githubusercontent.com/masaccio/ha-kingspan-watchman-sensit/main/images/configuration.png)

You can configure some parameters for the integration using by clicking **Configure** from the integration's entry in **Settings > Devices & Services** which is available through this helper:

[![Open your Home Assistant instance and show the SENSiT integration.](https://my.home-assistant.io/badges/integration.svg)](https://my.home-assistant.io/redirect/integration/?domain=kingspan_watchman_sensit)

The tank refresh interval configures how often the integration will request new data from the Kingspan service. The SENSiT tank transmitter only updates every 2 hours, but the timing is not configurable. It is therefore possible that the integration and the Kingspan service can not be well aligned, so this option allows for more frequent checks.

The usage interval is the number of days to average for oil usage. This is also used to calculate the predicted empty date.

## Energy Dashboard

[Home Assistant Energy Management](https://www.home-assistant.io/docs/energy/) doesn't include support for oil consumption, so you need to use gas instead. This integration provides a sensor `sensor.oil_consumption` which is the monotonically increasing amount of oil consumed represented as kWh.  The sensor is restored on restart and updated every day using the `sensor.current_usage` value.

The integration uses a simple conversion of 9.8kWh per litre of oil to calculate the energy usage in kWh. This value assumes 10.35 kWh per litre for heating oil and a boiler efficiency of 95%. The value can be configured in the integration's configuration.

You can add price information by locating a suitable online price source and scraping the value. In the UK, one such source is Home Fuels Direct which is a cheap broker for oil and publishes prices by UK county. Add the following template to you `configuration.yaml` adjusting the URL to your location and restart Home Assistant. The scan interval in this example is set to 24 hours.

``` yaml
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

With this you can configure gas consumption in Home Assistant by adding `sensor.oil_consumption` as your source of gas usage, then select "Use an entity with current price" and use your new `sensor.oil_price_per_litre` sensor as the price feed.
