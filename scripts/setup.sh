#!/bin/sh
# Interactive, local-only setup. Never commits keys or credentials.
set -eu
cd "$(dirname "$0")/.."
if [ -e .env ]; then
  printf 'File .env already exists; nothing changed.\n'
  exit 0
fi
printf 'Tuya device ID: '
IFS= read -r device_id
printf 'Tuya local IP: '
IFS= read -r device_ip
printf 'Zabbix technical host name: '
IFS= read -r host
printf 'Zabbix server address [127.0.0.1]: '
IFS= read -r zabbix_server
zabbix_server=${zabbix_server:-127.0.0.1}
printf 'Full path to TinyTuya devices.json [/Volume1/docker/tinytuya/devices.json]: '
IFS= read -r keyfile
keyfile=${keyfile:-/Volume1/docker/tinytuya/devices.json}
if [ -z "$device_id" ] || [ -z "$device_ip" ] || [ -z "$host" ]; then
  printf 'Device ID, IP, and host name cannot be empty.\n' >&2
  exit 1
fi
if [ ! -f "$keyfile" ]; then
  printf 'Cannot read devices.json: %s\n' "$keyfile" >&2
  exit 1
fi
case "$device_id$device_ip$host$zabbix_server$keyfile" in
  *'\n'*|*'\r'*) printf 'Newline in input is not allowed.\n' >&2; exit 1 ;;
esac
umask 077
cat > .env <<CONFIG
TZ=Asia/Almaty
TUYA_DEVICE_ID=$device_id
TUYA_DEVICE_IP=$device_ip
TUYA_VERSION=3.5
TUYA_DEVICES_FILE=$keyfile
ZABBIX_HOST=$host
ZABBIX_SERVER=$zabbix_server
ZABBIX_PORT=10051
POLL_INTERVAL_SECONDS=60
CONFIG
chmod 600 .env
printf 'Saved .env (permissions 600). Run: docker compose build && docker compose run --rm tinytuya-zabbix --dry-run\n'
