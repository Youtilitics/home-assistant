# Youtilitics for Home Assistant [![hacs][hacsbadge]][hacs]

[![Github Release][release-shield]][releases]
![issues]

A Home Assistant custom component to integrate electricity, gas and water data from Youtilitics.

## Installation via HACS (recommended)

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Youtilitics&repository=home-assistant)

1. Follow the link [here](https://hacs.xyz/docs/faq/custom_repositories/)
2. Use the custom repo link https://github.com/Youtilitics/home-assistant
3. Select the category type `integration`
4. Then once it's there (still in HACS) click the INSTALL button
5. Restart Home Assistant
6. Once restarted, in the HA UI go to `Configuration` (the ⚙️ in the lower left) -> `Devices and Services` click `+ Add Integration` and search for `Youtilitics`

## Using the Youtilitics component

**Configuration**

Upon activation of this custom component, you will need to add the credentials from your Youtilitics account into Home Assistant's app credentials.

You can retrieve your client ID/secret from your [Youtilitics profile](https://youtilitics.com/profile).

**Sensors**

This integration will add as many entities as there are service accounts in your Youtilitics account.

[hacs]: https://github.com/custom-components/hacs
[hacsbadge]: https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge
[releases]: https://github.com/Youtilitics/home-assistant/releases
[release-shield]: https://img.shields.io/github/v/release/Youtilitics/home-assistant
[issues]: https://img.shields.io/github/issues/Youtilitics/home-assistant

