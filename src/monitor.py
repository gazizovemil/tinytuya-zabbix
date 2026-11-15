#!/usr/bin/env python3
"""Read-only local TinyTuya polling and Zabbix trapper delivery."""
from __future__ import annotations

import argparse
import json
import logging
import os
import re
import socket
import struct
import time
from pathlib import Path

LOG = logging.getLogger("tinytuya-zabbix")


def env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def settings() -> dict:
    cfg = {
        "device_id": env("TUYA_DEVICE_ID"),
        "device_ip": env("TUYA_DEVICE_IP"),
        "version": float(env("TUYA_VERSION", "3.5")),
        "devices_file": Path(env("TUYA_DEVICES_FILE", "/config/devices.json")),
        "zabbix_host": env("ZABBIX_HOST"),
        "zabbix_server": env("ZABBIX_SERVER", "127.0.0.1"),
        "zabbix_port": int(env("ZABBIX_PORT", "10051")),
        "interval": max(15, int(env("POLL_INTERVAL_SECONDS", "60"))),
        "dps_relay": env("DPS_RELAY", "1"),
        "dps_current": env("DPS_CURRENT", "18"),
        "dps_power": env("DPS_POWER", "19"),
        "dps_voltage": env("DPS_VOLTAGE", "20"),
        "dps_countdown": env("DPS_COUNTDOWN", "9"),
        "dps_restore": env("DPS_RESTORE_MODE", "38"),
        "current_divisor": float(env("CURRENT_DIVISOR", "1000")),
        "power_divisor": float(env("POWER_DIVISOR", "10")),
        "voltage_divisor": float(env("VOLTAGE_DIVISOR", "10")),
    }
    if not cfg["device_id"] or not cfg["device_ip"] or not cfg["zabbix_host"]:
        raise ValueError("TUYA_DEVICE_ID, TUYA_DEVICE_IP and ZABBIX_HOST are required")
    if any(cfg[k] <= 0 for k in ("current_divisor", "power_divisor", "voltage_divisor")):
        raise ValueError("DPS divisors must be greater than zero")
    return cfg


def read_local_key(path: Path, device_id: str) -> str:
    data = json.loads(path.read_text(encoding="utf-8"))
    devices = data.get("devices", []) if isinstance(data, dict) else data
    if not isinstance(devices, list):
        raise ValueError("Invalid devices.json layout")
    for item in devices:
        if isinstance(item, dict) and str(item.get("id", item.get("dev_id", ""))) == device_id:
            key = item.get("key") or item.get("local_key") or item.get("localKey")
            if key:
                return key
            raise ValueError("Device found but Local Key is missing")
    raise ValueError("Device ID was not found in devices.json")


def numeric(dps: dict, key: str) -> float:
    value = dps.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"DPS {key} is missing or not numeric")
    return value


def decode_dps(dps: dict, cfg: dict) -> dict:
    relay = dps.get(cfg["dps_relay"])
    if not isinstance(relay, bool):
        raise ValueError("DPS relay is missing or not boolean")
    state = {
        "relay": int(relay),
        "current_a": round(numeric(dps, cfg["dps_current"]) / cfg["current_divisor"], 3),
        "power_w": round(numeric(dps, cfg["dps_power"]) / cfg["power_divisor"], 2),
        "voltage_v": round(numeric(dps, cfg["dps_voltage"]) / cfg["voltage_divisor"], 2),
        "dps": dps,
    }
    countdown = dps.get(cfg["dps_countdown"])
    if isinstance(countdown, (int, float)) and not isinstance(countdown, bool):
        state["countdown_s"] = int(countdown)
    restore = dps.get(cfg["dps_restore"])
    if restore is not None:
        state["restore_mode"] = str(restore)
    return state


def poll_device(cfg: dict) -> dict:
    # Lazy import keeps unit tests independent of hardware / third-party modules.
    import tinytuya

    local_key = read_local_key(cfg["devices_file"], cfg["device_id"])
    device = tinytuya.OutletDevice(
        dev_id=cfg["device_id"],
        address=cfg["device_ip"],
        local_key=local_key,
        version=cfg["version"],
    )
    device.set_socketTimeout(5)
    try:
        payload = device.status()
    finally:
        close = getattr(device, "close", None)
        if callable(close):
            close()
    if not isinstance(payload, dict) or not isinstance(payload.get("dps"), dict):
        raise ValueError("No valid DPS map in device response")
    return decode_dps(payload["dps"], cfg)


def read_exact(sock: socket.socket, count: int) -> bytes:
    parts = bytearray()
    while len(parts) < count:
        part = sock.recv(count - len(parts))
        if not part:
            raise ConnectionError("Zabbix closed connection prematurely")
        parts.extend(part)
    return bytes(parts)


def send_to_zabbix(cfg: dict, values: dict) -> str:
    request = {
        "request": "sender data",
        "data": [
            {"host": cfg["zabbix_host"], "key": key, "value": str(value)}
            for key, value in values.items()
        ],
    }
    body = json.dumps(request, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    with socket.create_connection((cfg["zabbix_server"], cfg["zabbix_port"]), timeout=10) as sock:
        sock.settimeout(10)
        sock.sendall(b"ZBXD\x01" + struct.pack("<Q", len(body)) + body)
        header = read_exact(sock, 13)
        if header[:5] != b"ZBXD\x01":
            raise RuntimeError("Bad Zabbix sender response header")
        length = struct.unpack("<Q", header[5:])[0]
        if length > 1024 * 1024:
            raise RuntimeError("Oversized Zabbix response")
        response = json.loads(read_exact(sock, length))
    info = response.get("info", "")
    processed = re.search(r"\bprocessed:\s*(\d+)", info)
    failed = re.search(r"\bfailed:\s*(\d+)", info)
    if (response.get("response") != "success" or not processed or not failed
            or int(failed.group(1)) != 0 or int(processed.group(1)) != len(values)):
        raise RuntimeError(f"Zabbix refused data: {response}")
    return info


def run_once(cfg: dict, dry_run: bool = False) -> bool:
    try:
        state = poll_device(cfg)
    except (OSError, ValueError, RuntimeError, KeyError) as exc:
        LOG.error("Tuya poll failed: %s", exc)
        if not dry_run:
            try:
                info = send_to_zabbix(cfg, {"tuya.poll.ok": 0})
                LOG.info("Zabbix accepted failure status: %s", info)
            except (OSError, ValueError, RuntimeError) as send_exc:
                LOG.error("Could not deliver failure status to Zabbix: %s", send_exc)
        return False

    LOG.info("Tuya OK: relay=%s voltage=%sV current=%sA power=%sW",
             state["relay"], state["voltage_v"], state["current_a"], state["power_w"])
    if dry_run:
        print(json.dumps(state, indent=2, ensure_ascii=False))
        return True
    try:
        info = send_to_zabbix(cfg, {
            "tuya.poll.ok": 1,
            "tuya.status.raw": json.dumps(state, separators=(",", ":"), ensure_ascii=False),
        })
    except (OSError, ValueError, RuntimeError) as exc:
        LOG.error("Tuya poll succeeded but Zabbix delivery failed: %s", exc)
        return False
    LOG.info("Zabbix accepted data: %s", info)
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Read Tuya smart plug and send to Zabbix")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--once", action="store_true", help="Poll once and send")
    mode.add_argument("--dry-run", action="store_true", help="Poll once without sending")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    try:
        cfg = settings()
    except (ValueError, OSError) as exc:
        LOG.error("Invalid configuration: %s", exc)
        raise SystemExit(2) from None
    LOG.info("Monitoring Tuya at %s; Zabbix host=%s", cfg["device_ip"], cfg["zabbix_host"])
    if args.once or args.dry_run:
        raise SystemExit(0 if run_once(cfg, dry_run=args.dry_run) else 1)
    while True:
        started = time.monotonic()
        run_once(cfg)
        time.sleep(max(1, cfg["interval"] - (time.monotonic() - started)))


if __name__ == "__main__":
    main()
