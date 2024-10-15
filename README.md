# USMS Smart Meter Custom Integration for Home Assistant

[USMS](https://www.usms.com.bn/smartmeter/about.html) is a digital platform for electric and water meters in Brunei. This integration allows Home Assistant to poll data from your USMS account.

Getting started is as easy as providing your login information (username and password), and Home Assistant will handle the rest. After configuration, the remaining unit, remaining credit and consumption history for all meters will be made available as sensor entities.

These entities can then be used to calculate and visualize useful statistics such as your monthly cost and average hourly/daily usage. The meter consumption entity can even be imported into Home Assistant's Energy dashboard.

> **Note:** For now only electric meters are supported since I do not have the smart water meter installed yet.

## Install

### If you have [HACS](https://hacs.xyz/) installed

- Open HACS
- Click on the 3-dot menu on the top right of the page
- Select `Custom repositories`
- Copy and paste this repository into the text field:
    ```https://github.com/azsaurr/ha-usms```
- Select `Integration` from the dropdown
- Click `Add`

### Manual installation

- Download the source code of this repository
- Extract the downloaded `.zip` file
- Copy and paste ```./config/custom_components/ha-usms``` from this repo to ```<home_assistant>/config/custom_components/ha-usms```

## Configuration

After installation:

- Open Settings
- Select `Devices & services`
- Click the floating blue `Add Integration` button
- Search for and select `HA-USMS`
- Enter your username and password
- Submit

## Usage

### Sensor Entities

| Entity              | Unit | Description |
| :---------------- | ------: | :---- |
| utility_meter_12345678        | kWh |   Current remaining unit.   |
| utility_meter_12345678_remaining_credit | BND |  Current remaining credit.   |
| utility_meter_12345678_last_updated    | Timestamp |  Last time data was updated.  |
| utility_meter_12345678_consumption           | - |   To be imported into Energy dashboard.   |

### Services

This integration provides the following useful services (which can be accessed from `Developer tools` > `Services`):

#### ha_usms.download_meter_consumption_history_service

Downloads and imports consumption history of a utility meter into their respective consumption entity as statistics (for that beautiful data visualization).

```yaml
service: ha_usms.download_meter_consumption_history_service
data:
  meter_no: "12345678"
  start: "1999-12-31"
  end: "2019-12-31"
```

> **Note:** Omitting `start` and `end` parameters will retrieve ALL consumption history. It is recommended to do this for every meter after initial setup.

#### ha_usms.recalculate_meter_sum_statistics_service

Recalculates statistics for historical consumptions, just in case there are anomalies that messes up your data visualization in Energy dashboard.

```yaml
service: ha_usms.recalculate_meter_sum_statistics_service
data:
  meter_no: "12345678"
```

#### ha_usms.update_meters_service

Perform a forced refresh for data now.

```yaml
service: ha_usms.update_meters_service
data: {}
```

#### ha_usms.calculate_utility_cost_response_service

Currently broken.

## To-Do

- [ ] Improve README
- [X] Re-structure source code files
- [X] Support for configuration via GUI
- [ ] Go through Home Assistant's [development checklist](https://developers.home-assistant.io/docs/development_checklist)
- [ ] Publish package to HACS store
- [ ] Support for water meter

## License

Distributed under the MIT License. See `LICENSE` for more information.

## Acknowledgments

- Home Assistant [documentation for developers](https://developers.home-assistant.io/docs/creating_component_index)
- [ludeeus/integration_blueprint](https://github.com/ludeeus/integration_blueprint)
- [USMS](https://www.usms.com.bn/smartmeter/about.html)
