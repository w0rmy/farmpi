"""End-to-end API/state tests with a transactional SQLite test adapter.

This exercises HTTP validation and persistent rows, not MariaDB DDL syntax.
The production migration still requires a MariaDB integration run.
"""
import contextlib
from datetime import datetime, timezone
import json
import os
import sqlite3
import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.ingest_api import SensorReadingRequest, router as ingest_router
from app.measurements import MEASUREMENTS
from app.node_api import router
from app.node_config import configuration, fingerprint, sync_state, validate_config


class Cursor:
    def __init__(self, connection):
        self.cursor = connection.cursor()

    def execute(self, sql, params=()):
        sql = sql.replace("%s", "?").replace(" FOR UPDATE", "").replace("UTC_TIMESTAMP(6)", "CURRENT_TIMESTAMP")
        sql = sql.replace("ON DUPLICATE KEY UPDATE hardware_uid=hardware_uid", "ON CONFLICT(hardware_uid) DO NOTHING")
        params = tuple(value.isoformat(" ") if isinstance(value, datetime) else value for value in params)
        self.cursor.execute(sql, params)
        self.lastrowid = self.cursor.lastrowid

    def fetchone(self):
        row = self.cursor.fetchone()
        if row is None:
            return None
        result = dict(row)
        for key in ("observed_at", "received_at", "last_seen"):
            if result.get(key):
                result[key] = datetime.fromisoformat(result[key])
        return result


class NodeFlowTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:", check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.executescript("""
        CREATE TABLE paddocks(id INTEGER PRIMARY KEY,name TEXT,active INTEGER);
        INSERT INTO paddocks VALUES(1,'Paddock A',1),(2,'Paddock B',1);
        CREATE TABLE sensor_nodes(id INTEGER PRIMARY KEY AUTOINCREMENT,node_uid TEXT UNIQUE,name TEXT,
          hardware_uid TEXT UNIQUE,device_key_hash TEXT,registration_state TEXT,active INTEGER,
          paddock_id INTEGER,firmware_version TEXT,board_profile TEXT,capabilities_json TEXT,
          desired_config_json TEXT,applied_config_json TEXT,desired_fingerprint TEXT,applied_fingerprint TEXT,
          failed_fingerprint TEXT,config_error TEXT,last_seen TEXT,location_epoch INTEGER DEFAULT 0);
        """)
        measurements = ",".join(m.key + " REAL" for m in MEASUREMENTS)
        self.db.execute(f"""CREATE TABLE readings(id INTEGER PRIMARY KEY,sensor_node_id INTEGER,paddock_id INTEGER,
            {measurements},simulated INTEGER,measurement_modes_json TEXT,observed_at TEXT,received_at TEXT,recorded_at TEXT,clock_valid INTEGER,
            clock_offset_seconds REAL,clock_out_of_tolerance INTEGER,sample_seq INTEGER,protocol_version INTEGER,
            UNIQUE(sensor_node_id,sample_seq))""")

        @contextlib.contextmanager
        def transaction():
            try:
                yield Cursor(self.db)
                self.db.commit()
            except Exception:
                self.db.rollback()
                raise

        self.patches = [patch("app.node_api.transaction", transaction), patch("app.managed_ingest.transaction", transaction), patch.dict(os.environ, {"FARMPI_ADMIN_TOKEN": "test-admin"})]
        for item in self.patches:
            item.start()
        app = FastAPI(); app.include_router(router); app.include_router(ingest_router)
        self.client = TestClient(app)
        self.admin = {"Authorization": "Bearer test-admin"}

    def tearDown(self):
        self.client.close()
        for item in reversed(self.patches):
            item.stop()
        self.db.close()

    def auth(self, number):
        return {"hardware_uid": f"{number:012x}", "device_key": f"{number:064x}"}

    def contact(self, number, applied=None):
        return self.client.post("/api/nodes/contact", json={**self.auth(number), "firmware_version": "test", "board_profile": "s3-test", "capabilities": ["soil_moisture_pct"], "applied_fingerprint": applied})

    def register(self, number):
        self.assertEqual(self.contact(number).status_code, 200)
        node_id = self.db.execute("SELECT id FROM sensor_nodes WHERE hardware_uid=?", (self.auth(number)["hardware_uid"],)).fetchone()[0]
        response = self.client.post(f"/api/nodes/{node_id}/approve", headers=self.admin, json={"name": f"Node {number}", "paddock_id": number})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertTrue(response.json()["registered"])
        return node_id

    def pull(self, number):
        response = self.client.post("/api/nodes/configuration", json=self.auth(number))
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def ack(self, number, config):
        return self.client.post("/api/nodes/ack", json={**self.auth(number), "config": config["config"], "fingerprint": config["fingerprint"]})

    def enable(self, number, node_id):
        old = self.pull(number)
        response = self.client.put(f"/api/nodes/{node_id}/configuration", headers=self.admin, json={"name": "Physical", "paddock_id": number, "modes": {"soil_moisture_pct": "LIVE"}, "expected_fingerprint": old["fingerprint"]})
        self.assertEqual(response.status_code, 200, response.text)
        config = self.pull(number)
        self.assertEqual(self.ack(number, config).status_code, 200)
        return config

    def sample(self, number, config, **extra):
        return {**self.auth(number), "sensor": config["config"]["node_uid"], "applied_fingerprint": config["fingerprint"], "location_epoch": 0,
            "simulated": False, "soil_moisture_pct": 21.5, "clock_valid": True, "device_time_unix": int(datetime.now(timezone.utc).timestamp()) - 1,
            "sample_seq": 1, **extra}

    def test_two_nodes_start_empty_and_sync_independently(self):
        first, second = self.register(1), self.register(2)
        one, two = self.pull(1), self.pull(2)
        self.assertEqual(one["config"]["modes"]["soil_moisture_pct"], "OFF")
        self.assertEqual(two["config"]["modes"]["soil_moisture_pct"], "OFF")
        self.ack(1, one); self.ack(2, two)
        enabled = self.enable(1, first)
        self.assertNotEqual(enabled["fingerprint"], one["fingerprint"])
        self.assertEqual(self.pull(2), two)
        self.assertEqual(self.contact(2, two["fingerprint"]).json()["sync_state"], "IN SYNC")
        self.assertEqual(self.contact(1, enabled["fingerprint"]).json()["sync_state"], "IN SYNC")
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM sensor_nodes").fetchone()[0], 2)

    def test_unapproved_cannot_pull_and_wrong_secret_cannot_impersonate(self):
        self.contact(1)
        self.assertEqual(self.client.post("/api/nodes/configuration", json=self.auth(1)).status_code, 403)
        self.assertEqual(self.client.post("/api/nodes/configuration", json={**self.auth(1), "device_key": "f" * 64}).status_code, 401)
        self.assertEqual(self.client.post("/api/nodes/1/approve", json={"name": "X"}).status_code, 401)

    def test_sparse_physical_reading_retry_and_cross_node_rejection(self):
        one = self.enable(1, self.register(1)); self.register(2)
        payload = self.sample(1, one)
        accepted = self.client.post("/api/ingest", json=payload)
        self.assertEqual(accepted.status_code, 201, accepted.text)
        self.assertEqual(accepted.json()["values"], {"soil_moisture_pct": 21.5})
        self.assertFalse(accepted.json()["simulated"])
        retry = self.client.post("/api/ingest", json=payload)
        self.assertTrue(retry.json()["deduplicated"], retry.text)
        for change, status in [({"sensor": "FP-002"}, 403), ({"simulated": True}, 422), ({"soil_moisture_pct": 22}, 422), ({"air_temperature_c": 18}, 422), ({"location_epoch": 1}, 422)]:
            with self.subTest(change=change):
                self.assertEqual(self.client.post("/api/ingest", json=payload | change).status_code, status)
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM readings").fetchone()[0], 1)

    def test_disabled_rejected_failure_preserves_applied_and_reboot_contact_recovers(self):
        node_id = self.register(1); empty = self.pull(1); self.ack(1, empty)
        self.assertEqual(self.client.post("/api/ingest", json=self.sample(1, empty)).status_code, 422)
        desired = self.enable(1, node_id)
        response = self.client.post("/api/nodes/ack", json={**self.auth(1), "fingerprint": "a" * 64, "error": "unsupported"})
        self.assertEqual(response.json()["sync_state"], "IN SYNC")
        # Reboot/missing state cannot falsely keep the previous IN SYNC state.
        self.assertEqual(self.contact(1).json()["sync_state"], "UPDATE PENDING")
        self.assertEqual(self.contact(1, desired["fingerprint"]).json()["sync_state"], "IN SYNC")

    def test_old_ack_does_not_overwrite_new_desired_and_approval_does_not_reset(self):
        node_id = self.register(1); old = self.pull(1); self.ack(1, old)
        latest = self.enable(1, node_id)
        self.assertEqual(self.ack(1, old).status_code, 409)
        self.client.post(f"/api/nodes/{node_id}/approve", headers=self.admin, json={"name": "Again"})
        self.assertEqual(self.pull(1), latest)

    def test_failed_update_retains_working_configuration(self):
        node_id = self.register(1)
        old = self.pull(1); self.ack(1, old)
        response = self.client.put(f"/api/nodes/{node_id}/configuration", headers=self.admin, json={"name": "Node", "paddock_id": 1, "modes": {"soil_moisture_pct": "LIVE"}, "expected_fingerprint": old["fingerprint"]})
        self.assertEqual(response.status_code, 200)
        desired = self.pull(1)
        failed = self.client.post("/api/nodes/ack", json={**self.auth(1), "fingerprint": desired["fingerprint"], "error": "NVS persistence failed"})
        self.assertEqual(failed.json()["sync_state"], "UPDATE FAILED")
        self.assertEqual(failed.json()["applied_fingerprint"], old["fingerprint"])
        bad = desired | {"config": desired["config"] | {"schema_version": 3}}
        self.assertEqual(self.ack(1, bad).status_code, 422)
        saved = self.db.execute("SELECT applied_config_json FROM sensor_nodes WHERE id=?", (node_id,)).fetchone()[0]
        self.assertEqual(json.loads(saved), old["config"])
        # Lost ack is repaired without walking intermediate configurations.
        self.assertEqual(self.contact(1, desired["fingerprint"]).json()["sync_state"], "IN SYNC")

    def test_relocation_preserves_history_and_rejects_old_assignment(self):
        node_id = self.register(1); config = self.enable(1, node_id)
        payload = self.sample(1, config)
        self.assertEqual(self.client.post("/api/ingest", json=payload).status_code, 201)
        response = self.client.put(f"/api/nodes/{node_id}/configuration", headers=self.admin, json={"name": "Moved", "paddock_id": 2, "modes": {"soil_moisture_pct": "LIVE"}, "expected_fingerprint": config["fingerprint"]})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.db.execute("SELECT paddock_id FROM readings").fetchone()[0], 1)
        self.assertEqual(self.contact(1, config["fingerprint"]).json()["location_epoch"], 1)
        self.assertEqual(self.client.post("/api/ingest", json=payload | {"sample_seq": 2}).status_code, 422)

        from app.farm_data import historical_rows_from
        def query(sql, params=None):
            cursor = Cursor(self.db); cursor.execute(sql, params or ())
            return [dict(row) for row in cursor.cursor.fetchall()]
        with patch("app.farm_data.fetch_all", query), patch("app.paddock_resolver.fetch_all", query):
            rows, name = historical_rows_from("soil_moisture_pct", datetime(2020, 1, 1, tzinfo=timezone.utc), "Paddock A")
        self.assertEqual(name, "Paddock A")
        self.assertEqual(rows[0]["sensor_uid"], config["config"]["node_uid"])
        self.assertEqual(rows[0]["value"], 21.5)

    def test_current_query_accepts_single_measurement_and_retains_source(self):
        from app.farm_data import get_environment_snapshot
        node_id = self.register(1); config = self.enable(1, node_id)
        self.assertEqual(self.client.post("/api/ingest", json=self.sample(1, config)).status_code, 201)
        def query(sql, params=None):
            cursor = Cursor(self.db)
            cursor.execute(sql.replace("JSON_ARRAYAGG", "JSON_GROUP_ARRAY"), params or ())
            rows = []
            while (row := cursor.fetchone()) is not None:
                rows.append(row)
            return rows
        with patch("app.farm_data.fetch_all", query):
            snapshot = get_environment_snapshot()
        self.assertEqual(snapshot[0].values, {"soil_moisture_pct": 21.5})
        self.assertEqual(snapshot[0].sources[0]["sensor"], config["config"]["node_uid"])
        self.assertFalse(snapshot[0].contains_simulated)

    def test_farmer_named_location_and_simulated_mode_are_explicit(self):
        created = self.client.post("/api/nodes/locations", headers=self.admin, json={"name": "Down by the Trough"})
        self.assertEqual(created.status_code, 200, created.text)
        self.assertEqual(created.json()["name"], "Down by the Trough")
        self.assertEqual(self.client.post("/api/nodes/locations", headers=self.admin, json={"name": "Down by the Trough"}).status_code, 409)

        node_id = self.register(1)
        old = self.pull(1)
        response = self.client.put(
            f"/api/nodes/{node_id}/configuration",
            headers=self.admin,
            json={"name": "Gate sensor", "paddock_id": 1, "modes": {"soil_moisture_pct": "SIMULATED"}, "expected_fingerprint": old["fingerprint"]},
        )
        self.assertEqual(response.status_code, 200, response.text)
        config = self.pull(1)
        self.assertEqual(self.ack(1, config).status_code, 200)
        payload = self.sample(1, config, simulated=True)
        accepted = self.client.post("/api/ingest", json=payload)
        self.assertEqual(accepted.status_code, 201, accepted.text)
        self.assertTrue(accepted.json()["simulated"])
        self.assertEqual(accepted.json()["measurement_modes"], {"soil_moisture_pct": "SIMULATED"})

    def test_unsupported_and_stale_admin_updates_do_not_mutate(self):
        node_id = self.register(1); old = self.pull(1)
        body = {"name": "Node", "paddock_id": 1, "modes": {"rainfall_mm": "LIVE"}, "expected_fingerprint": old["fingerprint"]}
        self.assertEqual(self.client.put(f"/api/nodes/{node_id}/configuration", headers=self.admin, json=body).status_code, 422)
        body.update(modes={"soil_moisture_pct": "OFF"}, expected_fingerprint="f" * 64)
        self.assertEqual(self.client.put(f"/api/nodes/{node_id}/configuration", headers=self.admin, json=body).status_code, 409)
        self.assertEqual(self.pull(1), old)


class ConfigurationTests(unittest.TestCase):
    def test_canonical_full_hash_and_validation(self):
        capabilities = ["soil_moisture_pct", "air_temperature_c"]
        config = configuration("node-001", capabilities, capabilities)
        self.assertEqual(len(fingerprint(config)), 64)
        self.assertEqual(fingerprint(config), fingerprint(configuration("node-001", list(reversed(capabilities)), capabilities)))
        for bad in [config | {"schema_version": 2}, config | {"node_uid": "FP-002"}, config | {"enabled": ["rainfall_mm"]}]:
            with self.assertRaises(ValueError):
                validate_config(bad, "node-001", capabilities, fingerprint(config))
        self.assertEqual(sync_state("a", "b", "a"), "UPDATE FAILED")
        self.assertEqual(sync_state("c", "b", "a"), "UPDATE PENDING")

    def test_strict_sparse_boundary(self):
        base = {"sensor": "FP-001", "soil_moisture_pct": 20.0}
        self.assertEqual(SensorReadingRequest(**base).soil_moisture_pct, 20)
        for changes in [{"soil_moisture_pct": True}, {"soil_moisture_pct": "20"}, {"soil_moisture_pct": None}, {"soil_moisture_pct": float("nan")}, {"unknown": 1}]:
            with self.subTest(changes=changes), self.assertRaises(ValidationError):
                SensorReadingRequest(**(base | changes))
