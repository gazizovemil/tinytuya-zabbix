import json
import os
import socket
import struct
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import monitor

CFG = {
    "device_id": "device-test-001", "device_ip": "192.0.2.10", "version": 3.5,
    "zabbix_host": "Test Smart Plug", "zabbix_server": "127.0.0.1", "zabbix_port": 10051,
    "dps_relay": "1", "dps_current": "18", "dps_power": "19", "dps_voltage": "20",
    "dps_countdown": "9", "dps_restore": "38", "current_divisor": 1000,
    "power_divisor": 10, "voltage_divisor": 10,
}


class DecodeTests(unittest.TestCase):
    def test_known_dps(self):
        result = monitor.decode_dps({"1": True, "9": 0, "18": 0, "19": 0,
                                     "20": 2227, "38": "memory", "40": False}, CFG)
        self.assertEqual(result["relay"], 1)
        self.assertEqual(result["voltage_v"], 222.7)
        self.assertEqual(result["power_w"], 0)
        self.assertEqual(result["current_a"], 0)
        self.assertEqual(result["restore_mode"], "memory")
        self.assertEqual(result["dps"]["40"], False)

    def test_other_dps_can_be_absent(self):
        state = monitor.decode_dps({"1": False, "18": 1250, "19": 128,
                                   "20": 2300}, CFG)
        self.assertEqual(state["current_a"], 1.25)
        self.assertEqual(state["power_w"], 12.8)
        self.assertNotIn("countdown_s", state)
        self.assertNotIn("restore_mode", state)

    def test_non_number_rejected(self):
        with self.assertRaises(ValueError):
            monitor.decode_dps({"1": True, "18": False, "19": 50, "20": 2200}, CFG)

    def test_missing_relay_rejected(self):
        with self.assertRaises(ValueError):
            monitor.decode_dps({"18": 0, "19": 0, "20": 2200}, CFG)

    def test_key_reading(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "devices.json"
            path.write_text(json.dumps([{"id": "device-test-001", "key": "local-test-key"}]))
            self.assertEqual(monitor.read_local_key(path, "device-test-001"), "local-test-key")

    def test_sender_error_does_not_report_device_failure(self):
        with patch.object(monitor, "poll_device", return_value={"relay":1,"voltage_v":220,"current_a":0,"power_w":0}):
            with patch.object(monitor, "send_to_zabbix", side_effect=RuntimeError("reject")) as send:
                self.assertFalse(monitor.run_once(CFG))
                self.assertEqual(send.call_count, 1)
                self.assertNotEqual(send.call_args.args[1], {"tuya.poll.ok":0})

    def test_device_failure_sends_failure_metric(self):
        with patch.object(monitor, "poll_device", side_effect=ValueError("bad DPS")):
            with patch.object(monitor, "send_to_zabbix", return_value="processed: 1; failed: 0") as send:
                self.assertFalse(monitor.run_once(CFG))
                self.assertEqual(send.call_args.args[1], {"tuya.poll.ok":0})


class SenderTests(unittest.TestCase):
    def _server(self, reply):
        sock = socket.socket()
        sock.bind(("127.0.0.1", 0))
        sock.listen(1)
        port = sock.getsockname()[1]
        received = {}

        def serve():
            try:
                conn, _ = sock.accept()
                with conn:
                    header = monitor.read_exact(conn, 13)
                    n = struct.unpack("<Q", header[5:])[0]
                    received.update(json.loads(monitor.read_exact(conn, n)))
                    body = json.dumps(reply).encode()
                    conn.sendall(b"ZBXD\x01" + struct.pack("<Q", len(body)) + body)
            finally:
                sock.close()

        thread = threading.Thread(target=serve, daemon=True)
        thread.start()
        return port, received, thread

    def test_sender_success(self):
        port, received, thread = self._server({"response":"success","info":"processed: 2; failed: 0; total: 2"})
        cfg = {**CFG, "zabbix_port": port}
        monitor.send_to_zabbix(cfg, {"tuya.poll.ok": 1, "tuya.status.raw": "{}"})
        thread.join(timeout=2)
        self.assertEqual(received["request"], "sender data")
        self.assertEqual(received["data"][0]["host"], "Test Smart Plug")

    def test_sender_reject(self):
        port, _, thread = self._server({"response":"success","info":"processed: 0; failed: 1; total: 1"})
        with self.assertRaises(RuntimeError):
            monitor.send_to_zabbix({**CFG,"zabbix_port":port}, {"tuya.poll.ok":1})
        thread.join(timeout=2)


if __name__ == "__main__":
    unittest.main()
