"""Static deployment contracts for the clean operational database baseline."""

from __future__ import annotations

from pathlib import Path
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class DatabaseMigrationTests(unittest.TestCase):
    def test_operational_seed_contains_no_synthetic_nodes_or_locations(self) -> None:
        seed = (PROJECT_ROOT / "config/database/seed.sql").read_text(encoding="utf-8")
        self.assertNotIn("Paddock A", seed)
        self.assertNotIn("test-moisture-", seed)
        self.assertIn("no locations, nodes or readings", seed)

    def test_reset_archives_before_recreating_database(self) -> None:
        helper = (PROJECT_ROOT / "scripts/reset-operational-database").read_text(encoding="utf-8")
        self.assertIn("mysqldump", helper)
        self.assertLess(helper.index("mysqldump"), helper.index("DROP DATABASE"))
        self.assertIn("--yes-really-reset", helper)
        self.assertIn("farmpi-pre-operational-reset-", helper)

    def test_normal_update_path_applies_schema_and_noop_seed(self) -> None:
        helper = (PROJECT_ROOT / "scripts/apply-database-schema").read_text(encoding="utf-8")
        update = (PROJECT_ROOT / "update").read_text(encoding="utf-8")
        self.assertIn('seed_file=${project_dir}/config/database/seed.sql', helper)
        self.assertIn('mariadb --protocol=socket farmpi < "${seed_file}"', helper)
        self.assertIn("scripts/apply-database-schema", update)

    def test_schema_has_time_sequence_and_measurement_provenance_contract(self) -> None:
        schema = (PROJECT_ROOT / "config/database/schema.sql").read_text(encoding="utf-8")
        for column in (
            "observed_at", "received_at", "clock_offset_seconds",
            "clock_out_of_tolerance", "sample_seq", "protocol_version",
            "measurement_modes_json",
        ):
            self.assertIn(column, schema)
        self.assertIn("uq_readings_sensor_sample_seq", schema)


if __name__ == "__main__":
    unittest.main()
