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

The integration reads data from the SENSiT sensor every 8 hours. The tank data is updated every 24 hours but 8 hours is chosen as the update point. Usage data and forcasts of empty are different from the Kingspan app. Rather than using just the previous day's reading, this integration uses the pasy 14 days as the basis for a prediction of empty, and the current usage is also the average of the past 14 days. These values can be changed in the [integration's configuration](#configuration).

![Lovelace Card for SENSiT integration](https://raw.githubusercontent.com/masaccio/ha-kingspan-watchman-sensit/main/images/lovelace-card.png)

## Configuration

![Configuration options for SENSiT integration](https://raw.githubusercontent.com/masaccio/ha-kingspan-watchman-sensit/main/images/configuration.png)

You can configure some parameters for the integration using by clicking **Configure** from the integration's entry in **Settings > Devices & Services** which is available through this helper:

[![Open your Home Assistant instance and show the SENSiT integration.](https://my.home-assistant.io/badges/integration.svg)](https://my.home-assistant.io/redirect/integration/?domain=kingspan_watchman_sensit)

The tank refresh interval configures how often the integration will request new data from the Kingspan service. The SENSiT tank transmitter only updates every 2 hours, but the timing is not configurable. It is therefore possible that the integration and the Kingspan service can not be well aligned, so this option allows for more frequent checks.

The usage interval is the number of days to average for oil usage. This is also used to calculate the predicted empty date.
