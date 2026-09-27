from pathlib import Path
import unittest


class ManagedNodeFirmwareTimeContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = (
            Path(__file__).resolve().parents[1]
            / "firmware"
            / "esp32-s3-node"
            / "esp32-s3-node.ino"
        ).read_text(encoding="utf-8")

    def test_managed_node_uses_contact_server_time_not_fake_ntp_service(self) -> None:
        self.assertNotIn('configTime(0, 0, "farmpi.local")', self.source)
        self.assertIn('response["server_time"]', self.source)
        self.assertIn("settimeofday(&tv, nullptr)", self.source)
        self.assertIn("syncClockFromFarmPi(response);", self.source)

    def test_contact_and_telemetry_cadence_are_unchanged(self) -> None:
        self.assertIn("CONTACT_INTERVAL_MS = 15000UL", self.source)
        self.assertIn("TELEMETRY_INTERVAL_MS = 60000UL", self.source)

    def test_telemetry_still_defers_when_clock_is_invalid(self) -> None:
        self.assertIn('if (now < 1700000000)', self.source)
        self.assertIn('Serial.println("Clock not ready; telemetry deferred.")', self.source)


if __name__ == "__main__":
    unittest.main()
