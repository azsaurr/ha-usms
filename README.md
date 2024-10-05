# USMS Smart Meter Custom Integration for Home Assistant

[USMS](https://www.usms.com.bn/smartmeter/about.html) is a digital platform for electric and water meters in Brunei. This integration allows Home Assistant to poll data from your USMS account.

Getting started is as easy as providing your login information (username and password), and Home Assistant will handle the rest. After configuration, the remaining unit (+ credit) and consumption history for all meters will be made available as sensor entities.

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
- Copy and paste the folder to:
    ```<home_assistant>/config/custom_components/```

## Configuration

So far only configuration via `configuration.yaml` file is supported.

### `configuration.yaml`
Add the following snippet to your ```<home_assistant>/config/configuration.yaml``` file:
```yaml
...

sensor:
  - platform: ha-usms
    username: "<username>"
    password: "<password>"

...
```

Adding Proxmox VE to your Home Assistant instance can be done via the UI using this button:

[![image](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start?domain=proxmoxve)

You can either use password or token based authentication. For user based authentication leave the
token name field empty. If you want to use token based authentication, fill the token name in the
corresponding input field and put your token secret in the password field.

### Manual Configuration

If the button above doesn't work, you can also perform the following steps manually:

* Navigate to your Home Assistant instance.
* In the sidebar, click Settings.
* From the Setup menu, select: Devices & Services.
* In the lower right corner, click the Add integration button.
* In the list, search and select `Proxmox VE`.
* Follow the on-screen instructions to complete the setup.

## To-Do

- [ ] Improve README
- [ ] Re-structure source code files
- [ ] Support for configuration via GUI
- [ ] Go through Home Assistant's [development checklist](https://developers.home-assistant.io/docs/development_checklist)
- [ ] Publish package to HACS store
- [ ] Support for water meter


## License

Distributed under the MIT License. See `LICENSE` for more information.


## Acknowledgments

* []() Home Assistant [documentation for developers](https://developers.home-assistant.io/docs/creating_component_index)
* []() [USMS](https://www.usms.com.bn/smartmeter/about.html)
