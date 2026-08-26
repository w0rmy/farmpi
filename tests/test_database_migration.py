"""Static deployment contracts for the repeatable 16-node database migration."""

from __future__ import annotations

from pathlib import Path
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class DatabaseMigrationTests(unittest.TestCase):
    def test_seed_declares_all_sixteen_stable_sensor_uids(self) -> None:
        seed = (PROJECT_ROOT / "config/database/seed.sql").read_text(encoding="utf-8")
        for suffix in "abcdefghijklmnop":
            self.assertIn(f"SELECT '{suffix}'", seed)
        self.assertIn("^test-moisture-[a-p]$", seed)

    def test_repeatable_seed_never_reassigns_existing_sensor_paddock(self) -> None:
        seed = (PROJECT_ROOT / "config/database/seed.sql").read_text(encoding="utf-8")
        self.assertNotIn("paddock_id = VALUES(paddock_id)", seed)
        self.assertIn("WHERE s.id IS NULL", seed)
        self.assertIn("p.id = s.paddock_id", seed)

    def test_normal_update_path_applies_schema_and_seed(self) -> None:
        helper = (PROJECT_ROOT / "scripts/apply-database-schema").read_text(encoding="utf-8")
        update = (PROJECT_ROOT / "update").read_text(encoding="utf-8")
        self.assertIn('seed_file=${project_dir}/config/database/seed.sql', helper)
        self.assertIn('mariadb --protocol=socket farmpi < "${seed_file}"', helper)
        self.assertIn('scripts/apply-database-schema', update)

    def test_schema_has_observation_receive_and_sequence_contract(self) -> None:
        schema = (PROJECT_ROOT / "config/database/schema.sql").read_text(encoding="utf-8")
        for column in ("observed_at", "received_at", "clock_offset_seconds", "clock_out_of_tolerance", "sample_seq", "protocol_version"):
            self.assertIn(column, schema)
        self.assertIn("uq_readings_sensor_sample_seq", schema)


if __name__ == "__main__":
    unittest.main()
