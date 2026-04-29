# Cloudflare Advanced (for Home Assistant)

[![GitHub Release](https://img.shields.io/github/release/FaserF/ha-cloudflare.svg?style=flat-square)](https://github.com/FaserF/ha-cloudflare/releases)
[![License](https://img.shields.io/github/license/FaserF/ha-cloudflare.svg?style=flat-square)](LICENSE)
[![hacs](https://img.shields.io/badge/HACS-custom-orange.svg?style=flat-square)](https://hacs.xyz)
[![Add to Home Assistant](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=cloudflare_advanced)
[![CI Orchestrator](https://github.com/FaserF/ha-cloudflare/actions/workflows/ci-orchestrator.yml/badge.svg)](https://github.com/FaserF/ha-cloudflare/actions/workflows/ci-orchestrator.yml)

A secure, production-ready Home Assistant integration for Cloudflare. Monitor zone analytics, manage Zero Trust tunnels, control page rules, secure apps, and modify DNS records directly from Home Assistant.

## 🧭 Quick Links

| | | | |
| :--- | :--- | :--- | :--- |
| [✨ Features](#-features) | [📦 Installation](#-installation) | [⚙️ Configuration](#️-configuration) | [🛡️ Security](#-security) |
| [🧱 Services](#-services) | [📖 Automations](#-automation-examples) | [❓ FAQ](#-troubleshooting--faq) | [🧑‍💻 Development](#-development) |
| [💖 Credits](#-credits--acknowledgements) | [📄 License](#-license) | | |

### Why use this integration?
While generic DNS updates only provide simple IP changes, this integration leverages Cloudflare APIs (REST & GraphQL) to offer deep administrative control. Manage multiple zones, workers, turnstile widgets, access policies, and Zero Trust tunnels in one cohesive dashboard without accessing complex terminals.

## ✨ Features

- **Zone Analytics**: 
  - **Requests**: Real-time traffic insights.
  - **Bandwidth**: Data transfer metrics (in Megabytes).
  - **Threats Blocked**: See how many malicious requests were prevented.
  - **Unique Visitors**: Track visitor metrics.
- **Zero Trust & Tunnels**: 
  - **Tunnel Status**: Monitor status (Connected/Healthy) for Cloudflare Tunnels.
  - **Details**: Track active connection counts and connector daemon versions.
- **Access Applications, Edge Workers & Pages**: 
  - **Access Apps**: Monitor active statuses for protected assets.
  - **Workers Deployment**: Get uptime diagnostics for deployed Cloudflare Workers.
  - **Pages Deployment**: Track the live deployment state of Cloudflare Pages.
  - **Turnstile Widgets**: Monitor mode configurations.
- **Configurable Control**:
  - **Zone Settings**: Toggles for Development Mode, Always Use HTTPS, and Automatic HTTPS Rewrites.
  - **Security Level**: Dropdown options to force immediate strictness (`off`, `essentially_off`, `low`, `medium`, `high`, `under_attack`).
  - **Page Rules**: Disable or enable individual URL filters.
  - **Security Logs**: Tracks external attack properties (`Country`, `IP Address`, `Rule Triggered`).
- **Smart Tracking & Logic**:
  - **Automated DDNS Updates**: Automatically detects your router's public IP changes using `Home Assistant` networking infrastructure, seamlessly propagating dynamic changes onto mapped Zone A-Records.
  - **Cache Management**: Instantly purge your Cloudflare Zone Cache using custom hardware buttons.

## ❤️ Support This Project

> I maintain this integration in my **free time alongside my regular job** — bug hunting, new features, testing. Test environments cost money, and every donation helps me stay independent and dedicate more time to open-source work.
>
> **This project is and will always remain 100% free.** There are no "Premium Upgrades" or subscriptions.
>
> Donations are completely voluntary — but the more support I receive, the less I depend on other income sources. 💪

<div align="center">

[![GitHub Sponsors](https://img.shields.io/badge/Sponsor%20on-GitHub-%23EA4AAA?style=for-the-badge&logo=github-sponsors&logoColor=white)](https://github.com/sponsors/FaserF)&nbsp;&nbsp;
[![PayPal](https://img.shields.io/badge/Donate%20via-PayPal-%2300457C?style=for-the-badge&logo=paypal&logoColor=white)](https://paypal.me/FaserF)

</div>

## 📦 Installation

### HACS (Recommended)

This integration is fully compatible with [HACS](https://hacs.xyz/).

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=FaserF&repository=ha-cloudflare&category=Integration)

1. Open HACS in Home Assistant.
2. Click the three dots in the top right corner and select **Custom repositories**.
3. Add `FaserF/ha-cloudflare` with category **Integration**.
4. Search for "Cloudflare Advanced".
5. Install and restart Home Assistant.

### Manual Installation

1. Download the latest release from the [Releases page](https://github.com/FaserF/ha-cloudflare/releases).
2. Extract the `custom_components/cloudflare_advanced` folder into your Home Assistant's `custom_components` directory.
3. Restart Home Assistant.

## ⚙️ Configuration

Adding your Cloudflare account is entirely done via the UI. **No YAML configuration is required.**

1. Navigate to **Settings > Devices & Services** in Home Assistant.
2. Click **Add Integration** and search for **Cloudflare Advanced**.
3. Choose Authentication:
   - **API Token (Recommended)**: Generate a secure scoped token.
   - **Legacy Credentials**: E-Mail address + Global API Key.
4. Select which active domain zones you wish to initialize.

## 🛡️ Security

To use the recommended API Token method, you must generate a token in your Cloudflare account.

You can jump directly to the [Cloudflare API Tokens Dashboard](https://dash.cloudflare.com/profile/api-tokens) or follow these steps manually:
1. Log in to the [Cloudflare Dashboard](https://dash.cloudflare.com/).
2. In the top right, click on your **Profile Icon** and select **My Profile**.
3. Go to the **API Tokens** tab.
4. Click **Create Token** and select **Create Custom Token**.

For a comprehensive step-by-step tutorial, refer to the official [Cloudflare Token Creation Guide](https://developers.cloudflare.com/fundamentals/api/get-started/create-token/).

Ensure your generated API Token follows the **Principle of Least Privilege**. Grant access solely to the required scopes for your selected domains:
- `Zone.Analytics` (Read)
- `Zone.Zone` (Read)
- `Zone.Settings` (Read/Edit)
- `Zone.Page Rules` (Read/Edit)
- `Zone.Cache Purge` (Edit)
- `Zone.DNS` (Read/Edit)

*Optional scopes for Account-wide assets (Tunnels, Workers, Turnstile, Access Apps):*
- `Account.Cloudflare Zero Trust` (Read)
- `Account.Workers Scripts` (Read)


## 🧱 Services

The integration provides powerful actions for deployment management.

### `cloudflare_advanced.purge_cache`
Purges files stored on edge cache layers.
- **`zone_id`**: (Required) Unique identifier of the domain zone.
- **`purge_everything`**: (Optional) Clears all cached elements if True (default: `true`).
- **`files`**: (Optional) Specify exact asset URLs to selectively wipe.

### `cloudflare_advanced.update_dns_record`
Updates IP targets.
- **`zone_id`**: (Required) Target Cloudflare Zone.
- **`record_id`**: (Required) Cloudflare record reference.
- **`name`**: (Required) Record name string (e.g. `sub.example.com`).
- **`type`**: (Required) Protocol format (`A`, `CNAME`, `AAAA`).
- **`content`**: (Required) Upstream destination.

### `cloudflare_advanced.create_dns_record`
Constructs completely new entries.
- **`zone_id`**: (Required) Domain reference.
- **`name`**: (Required) Title endpoint string.
- **`type`**: (Required) Schema type.
- **`content`**: (Required) IP binding.

## 📖 Automation Examples

<details>
<summary><strong>🔄 Auto-Disable Dev Mode After Hours</strong></summary>

```yaml
alias: "Cloudflare: Time Dev Mode"
trigger:
  - platform: state
    entity_id: switch.example_com_development_mode
    to: "on"
    for:
      hours: 4
action:
  - target:
      entity_id: switch.example_com_development_mode
    action: switch.turn_off
```
</details>

<details>
<summary><strong>🛡️ Respond to Threat Spikes</strong></summary>

```yaml
alias: "Cloudflare: Under Attack State"
trigger:
  - platform: numeric_state
    entity_id: sensor.example_com_threats_blocked
    above: 25
action:
  - target:
      entity_id: select.example_com_security_level
    action: select.select_option
    data:
      option: "under_attack"
```
</details>

<details>
<summary><strong>🚨 Push Alerts on VPN Tunnel Failures</strong></summary>

```yaml
alias: "Cloudflare: Tunnel Status Notification"
trigger:
  - platform: state
    entity_id: binary_sensor.tunnel_main_gateway
    to: "off"
action:
  - action: notify.notify
    data:
      title: "Tunnel Error"
      message: "Gateway link dropped."
```
</details>

## ❓ Troubleshooting & FAQ

### "Invalid Auth" during setup
Check token permissions. Tokens restricted from accessing general lists fail verification. Verify Zone read privileges.

### Why are some controls missing?
Specific operations rely upon the Tier setup in Cloudflare profiles. Free profiles lack some complex variables.

## 🧑‍💻 Development

Uses:
- `ruff` linting
- `pytest` frameworks
- `mypy` validation

## 💖 Credits & Acknowledgements

Built from the ground up to provide a complete replacement for basic dynamic IP workflows.

## 📄 License

MIT License - see the [LICENSE](LICENSE) file for details.
