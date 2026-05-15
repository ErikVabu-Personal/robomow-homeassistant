# Robomow3 — Home Assistant Integration

Custom Home Assistant integration for Robomow robotic mowers connected via the Robomow cloud.

## Features

- **LawnMowerEntity** with start, pause, and dock (return to base) controls
- Sensors: battery level, battery state, mower state, WiFi signal, WiFi network, next scheduled mowing, mow time, mow debt, last seen, firmware version
- Cloud polling every 60 seconds via the Robomow REST API

## Installation

1. Copy the `custom_components/robomow3/` folder into your Home Assistant `config/custom_components/` directory.
2. Restart Home Assistant.
3. Go to **Settings > Integrations > Add Integration** and search for **Robomow3**.
4. Sign in with your Robomow3 app credentials.
5. Select your mower if you have multiple devices.

## Requirements

- Home Assistant 2024.1+
- A Robomow account with a connected mower (tested with M800 / RK platform)
- Internet access (cloud-based integration)

## Protocol Details

This integration was built by reverse-engineering the Robomow 3.0 Android app (v3.5.6). It uses three API backends:

- **Authentication**: `https://myrobomow.robomow.com/api/v2/mobile/authenticate`
- **Device API**: AWS API Gateway REST endpoints (`api/V6/{brand}/device/{deviceId}/...`) for dashboard, settings, start/stop mowing, and scheduler
- **Go-Home (Return to Base)**: AWS IoT Device Shadow REST API on port 8443 with mutual-TLS (client certificate obtained via `get-client-certificate-pfx` endpoint). The go-home command is not available via the REST API; the app uses MQTT shadow updates with `returnToBase` in the desired state

## Disclaimer

This is an unofficial integration. It is not affiliated with, endorsed by, or supported by Robomow/MTD Products. Use at your own risk.
