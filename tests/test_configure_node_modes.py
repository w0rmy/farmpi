"""Exercise the console helper without a deployed API or administrator secrets."""
import contextlib
import io
from pathlib import Path
import runpy
import sys
import unittest
from unittest.mock import patch


class ConfigureNodeModesTests(unittest.TestCase):
    def setUp(self):
        self.command = runpy.run_path(str(Path(__file__).resolve().parents[1] / "scripts/configure-node-modes"))
        self.node = {"id": 1, "node_uid": "FP-001", "name": "Gate sensor", "paddock_id": 2,
            "desired_fingerprint": "a" * 64, "sensors": [
                {"key": "soil_moisture_pct", "supported": True, "mode": "OFF", "live_supported": False},
                {"key": "air_temperature_c", "supported": True, "mode": "SIMULATED", "live_supported": False},
                {"key": "rainfall_mm", "supported": False, "mode": "OFF"}]}

    def invoke(self, assignment, api):
        namespace = self.command["main"].__globals__
        with patch.dict(namespace, {"api": api, "read_admin_token": lambda: "test-only"}), \
                patch.object(sys, "argv", ["configure-node-modes", "FP-001", assignment]), \
                patch("time.sleep"), contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            self.command["main"]()

    def test_console_patch_preserves_other_modes_identity_and_fingerprint(self):
        writes = []
        def api(path, token, method="GET", body=None):
            if method == "PUT":
                writes.append(body)
                return {"fingerprint": "b" * 64}
            node = self.node if not writes else self.node | {"desired_fingerprint": "b" * 64, "sync_state": "IN SYNC"}
            return {"nodes": [node]}
        self.invoke("soil_moisture_pct=SIMULATED", api)
        self.assertEqual(writes, [{"name": "Gate sensor", "paddock_id": 2,
            "expected_fingerprint": "a" * 64,
            "modes": {"soil_moisture_pct": "SIMULATED", "air_temperature_c": "SIMULATED"}}])

    def test_unsupported_live_and_measurements_never_send_an_update(self):
        for assignment in ("soil_moisture_pct=LIVE", "rainfall_mm=SIMULATED"):
            with self.subTest(assignment=assignment):
                def api(path, token, method="GET", body=None):
                    self.assertEqual(method, "GET")
                    return {"nodes": [self.node]}
                with self.assertRaises(SystemExit) as error:
                    self.invoke(assignment, api)
                self.assertEqual(error.exception.code, 2)
