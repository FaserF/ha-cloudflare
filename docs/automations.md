# Automation Examples

## 🔄 Auto-Disable Dev Mode After Hours

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

## 🛡️ Respond to Threat Spikes

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

## 🚨 Push Alerts on VPN Tunnel Failures

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
