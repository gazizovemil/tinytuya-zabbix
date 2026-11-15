# TinyTuya → Zabbix Monitor

[Русская документация](README.ru.md) · [Configuration reference](docs/CONFIGURATION.md) · [License](LICENSE)

Read-only monitoring of Wi-Fi Tuya smart plugs via **TinyTuya (local LAN)** and **Zabbix 8.2**, packed in a minimal Python Docker image. **No Home Assistant, host-side Python, Tuya Cloud API calls during polling, or SNMP** is required.

> This is a community project and is not affiliated with Tuya, TinyTuya, or Zabbix. Local network protocol support varies by device and firmware.

## Features

- Local status polling (defaults to every 60 seconds); Tuya protocol v3.5 by default.
- Relay on/off, voltage (V), current (A), power (W), optional countdown and power-on restore mode.
- One Zabbix trapper health item `tuya.poll.ok` and one JSON trapper master item `tuya.status.raw`. Dependent items, three graphs, and triggers are provided by the bundled Zabbix template.
- Minimal and read-only: only calls `status()`. No commands that toggle the relay.
- Safe handling of delivery failures: an unreachable Zabbix Server is **not** recorded as a Tuya device failure.
- Works with a read-only TinyTuya `devices.json` containing the Local Key. Does not require a cloud API token at runtime.
- Single-device per container, multiple containers can use the same image with different configurations.

**Energy note:** instantaneous power is **not** a cumulative kWh counter. A native cumulative energy reading is not inferred from unspecified DPS fields.

## Requirements

- Docker Engine and Docker Compose v2 (e.g., on TerraMaster TOS).
- A reachable LAN Tuya Wi-Fi socket/plug and its **Device ID**, local IP, protocol version, and **Local Key**.
- A local TinyTuya `devices.json` produced by the TinyTuya wizard. A key previously obtained for the device is required; do not commit the file.
- Zabbix Server with reachable TCP port 10051, and a host with the correct technical name.

## Quick start (local Docker build)

1. Download/extract the source repository. Keep it in a dedicated directory, such as `/Volume1/docker/tinytuya-zabbix`.
2. Import `zabbix/Tuya_Smart_Plug_by_TinyTuya_Zabbix_8.2.xml` from **Data collection → Templates → Import**.
3. Create a host with template **Tuya Smart Plug by TinyTuya**. No Agent/SNMP interface is required. Note the *technical host name* (not merely the display name).
4. Configure access from the sending container: in the two **Zabbix trapper** items `tuya.poll.ok` and `tuya.status.raw`, fill in **Allowed hosts** with the IP that Zabbix Server sees (commonly the host's Docker bridge gateway, not `127.0.0.1`). This can also be represented by a Zabbix user macro. Restrict TCP 10051 to trusted networks.
5. Run the setup, which asks interactively for your own values and creates an untracked, mode-0600 `.env` file:

```sh
cd /Volume1/docker/tinytuya-zabbix
./scripts/setup.sh
docker compose build
docker compose run --rm tinytuya-zabbix --dry-run
docker compose run --rm tinytuya-zabbix --once
docker compose up -d
docker compose logs --tail=30 -f tinytuya-zabbix
```

`--dry-run` displays the decoded metrics without sending to Zabbix. `--once` sends them and exits. `up -d` performs the recurring polling. If Zabbix is exposed on the TNAS host's port 10051 and host networking is enabled, `127.0.0.1` is a valid Zabbix Server address.

To stop:

```sh
docker compose down
```

## Using the Docker Hub image

After an image is published under your Docker Hub account, configure `DOCKERHUB_USERNAME` in your local `.env`, then run:

```sh
docker compose -f compose.hub.yaml pull
docker compose -f compose.hub.yaml up -d
```

No software is installed directly into the NAS operating system; containers contain Python and TinyTuya.

## Zabbix metrics

| Item | Key | Source |
|---|---|---|
| Poll health | `tuya.poll.ok` | 1 on successful local poll, 0 on failed local poll |
| Raw JSON | `tuya.status.raw` | Decoded state + original DPS |
| Relay | `tuya.relay` | DPS 1, 1/0 |
| Voltage | `tuya.voltage` | DPS 20 / 10, volts |
| Current | `tuya.current` | DPS 18 / 1000, amperes |
| Power | `tuya.power` | DPS 19 / 10, watts |
| Countdown | `tuya.countdown` | DPS 9, optional |
| Restore mode | `tuya.restore.mode` | DPS 38, optional |

The DPS mapping and divisors are configurable. Defaults match one tested Tuya plug; vendors may use different codes or scaling. Validate against your device's product definitions or live DPS samples before relying on power or voltage alerts.

Included triggers: three failed polls, five minutes without data, voltage outside adjustable bounds, and high power. Tune the template macros `{$TUYA.POWER.MAX}`, `{$TUYA.VOLT.MIN}`, `{$TUYA.VOLT.MAX}` to your installation.

## Security

- **Never publish** `devices.json`, `.env`, TinyTuya snapshots, Tuya Cloud credentials, or Local Key. `.gitignore` and `.dockerignore` exclude common secret files.
- The local key is read from a file mounted read-only at `/config/devices.json`; it is never copied into the built image.
- The container uses a read-only root filesystem, no added privileges, all Linux capabilities dropped, and a temporary `/tmp` filesystem.
- The container uses host networking for direct LAN access. Do not expose the Tuya device's local port or Zabbix port to the public internet.
- Zabbix sender protocol on TCP 10051 is **not encrypted by this project**. Use only a trusted network or a secure tunnel / Zabbix TLS-capable sender gateway.
- Restrict **Allowed hosts** for both Zabbix trapper items; this must match the **IP as observed by Zabbix Server**, which may be a Docker NAT gateway.

## Troubleshooting

| Symptom | Check |
|---|---|
| `Device ID was not found` | Correct ID and mounted `devices.json` |
| `No valid DPS map` | Local Key, LAN access, protocol version; do not assume every model uses the same codes |
| `processed: 0; failed: 2` | Zabbix host's technical name, enabled trapper items, Allowed hosts IP, template, Zabbix configuration cache |
| `Connection refused` | Server listening on port 10051; Docker networking and firewall |
| `tuya.poll.ok=0` | Device polling failed; check device and Local Key |
| `tuya.poll.ok` stops updating | Docker stopped or sender couldn't reach Zabbix; inspect container logs and `nodata()` trigger |

On Zabbix, the two required *trapper* items must be enabled. After updating configuration, use `zabbix_server -R config_cache_reload` where available.

## Contributing and testing

```sh
python3 -m unittest discover -s tests -v
python3 -m compileall -q src
```

CI runs tests and a Docker build on GitHub. See [Publishing guide](docs/PUBLISHING.md) for publishing the source to GitHub and the image to Docker Hub (local or automated multi-architecture release).

The included Zabbix template **retains the UUIDs** of the original imported template to support updating existing installations. Exporting/importing from a different Zabbix minor version should be tested first.

## Credits

Uses [TinyTuya](https://github.com/jasonacox/tinytuya) by its maintainers. Zabbix is a trademark of Zabbix LLC. The project code and docs are MIT-licensed; third-party packages retain their own licenses.
