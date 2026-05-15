# Robomow3 — Home Assistant Integration

Custom Home Assistant integration for Robomow robotic mowers connected via the Robomow cloud.

## Features

- **LawnMowerEntity** with start, pause, and dock (return to base) controls
- Sensors: battery level, battery state, mower state, WiFi signal, WiFi network, next scheduled mowing, mow time, mow debt, last seen, firmware version
- Cloud polling every 60 seconds via the Robomow REST API
- All commands (start, stop, return to base) work over the cloud — no Bluetooth required

## Installation

1. Copy the `custom_components/robomow3/` folder into your Home Assistant `config/custom_components/` directory.
2. Restart Home Assistant.
3. Go to **Settings > Integrations > Add Integration** and search for **Robomow3**.
4. Sign in with your Robomow3 app credentials.
5. Select your mower if you have multiple devices.

## Requirements

- Home Assistant 2024.1+
- A Robomow account with a connected mower (tested with RK platform, e.g. RK1000)
- Internet access (cloud-based integration)

## Protocol Details

This integration was built by reverse-engineering the Robomow 3.0 Android app (v3.5.6). It uses two API backends:

- **Authentication**: `https://myrobomow.robomow.com/api/v2/mobile/authenticate` — returns a JWT access token
- **Device API**: AWS API Gateway REST endpoints (`api/V6/{brand}/device/{deviceId}/...`) for dashboard, settings, start/stop mowing, scheduler, and return-to-base

### Commands

- **Start mowing**: `POST start-mowing` with `{"zone": 0, "edge": false, "duration": "0", "returnToBase": false}`
- **Stop mowing**: `POST stop-mowing`
- **Return to base**: `POST start-mowing` with `{"zone": 0, "edge": false, "duration": "0", "returnToBase": true}` — discovered from the APK's `StartMowingRequest` model; the same endpoint handles both mowing and return-to-base

## Disclaimer

This is an unofficial integration. It is not affiliated with, endorsed by, or supported by Robomow/MTD Products. Use at your own risk.
