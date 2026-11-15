# Configuration reference (English)

The `./scripts/setup.sh` wizard creates the untracked `.env` file. It asks for the device ID, LAN IP, technical host name from Zabbix, Zabbix Server address, and absolute path to the existing TinyTuya `devices.json`. The file is created with `0600` permissions.

## Environment variables

| Variable | Required | Default | Meaning |
|---|---|---|---|
| `TUYA_DEVICE_ID` | yes | — | Tuya device identifier; must match `devices.json` |
| `TUYA_DEVICE_IP` | yes | — | Local IP address of smart plug |
| `TUYA_DEVICES_FILE` | yes | `/config/devices.json` inside container | TinyTuya local key file; Compose mounts the host path at `/config/devices.json` |
| `TUYA_VERSION` | no | `3.5` | LAN protocol version (set to the actual supported version) |
| `ZABBIX_HOST` | yes | — | Zabbix **technical** host name (case-sensitive) |
| `ZABBIX_SERVER` | no | `127.0.0.1` | Zabbix sender endpoint accessible from container |
| `ZABBIX_PORT` | no | `10051` | Zabbix trapper port |
| `POLL_INTERVAL_SECONDS` | no | `60` | Poll interval, minimum 15 seconds |
| `DPS_RELAY` | no | `1` | Relay state key |
| `DPS_CURRENT` | no | `18` | Current key |
| `DPS_POWER` | no | `19` | Power key |
| `DPS_VOLTAGE` | no | `20` | Voltage key |
| `DPS_COUNTDOWN` | no | `9` | Optional countdown key |
| `DPS_RESTORE_MODE` | no | `38` | Optional restore mode key |
| `CURRENT_DIVISOR` | no | `1000` | Raw current / divisor → A |
| `POWER_DIVISOR` | no | `10` | Raw power / divisor → W |
| `VOLTAGE_DIVISOR` | no | `10` | Raw voltage / divisor → V |
| `DOCKERHUB_USERNAME` | for `compose.hub.yaml` | — | Docker Hub namespace for image |
| `IMAGE_TAG` | no | `latest` | Published image tag |

For alternative models, inspect their DPS using TinyTuya before changing these settings. A missing optional countdown or restore code causes the corresponding dependent item to receive no new value, not a fabricated zero.

### Multi-device deployments

Run one container per smart plug, each using a separate `.env` and container name. You may reuse the same Docker image and the same host TinyTuya `devices.json` mounted read-only. Ensure `ZABBIX_HOST` is unique and matches the corresponding Zabbix host.

### Access control

Zabbix trapper items allow values only from configured **Allowed hosts**. A container running `network_mode: host` on a NAS does **not** necessarily appear to Zabbix Server as `127.0.0.1`, when the server itself runs in a separate Docker bridge network. Inspect the `Gateway` of the Zabbix Server's Docker network and verify the real sender address in the server logs. Then configure the Allowed hosts on both `tuya.poll.ok` and `tuya.status.raw`, directly or via a macro. Reload Zabbix configuration if necessary.
