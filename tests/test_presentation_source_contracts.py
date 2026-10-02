"""Source-level regressions for managed simulation and Android drill-down intent.

These checks do not replace Arduino/Android builds; they protect high-level design
contracts in environments where those toolchains are not installed.
"""

from __future__ import annotations

from pathlib import Path
import unittest


class PresentationSourceContractTests(unittest.TestCase):
    def test_managed_simulation_is_not_one_hour_sine_wave(self) -> None:
        source = Path("firmware/esp32-s3-node/esp32-s3-node.ino").read_text(encoding="utf-8")
        profile = Path("firmware/esp32-s3-node/board_profile.h").read_text(encoding="utf-8")

        self.assertNotIn("millis() % 3600000UL", source)
        self.assertIn("FARM_TIMEZONE", source)
        self.assertIn("NZ_SIMULATION_LATITUDE", source)
        self.assertIn("daylightFraction", source)
        self.assertIn("rainEventFor", source)
        self.assertIn('static const char* FIRMWARE_VERSION = "', profile)
        self.assertIn('"soil_moisture_pct"', profile)

    def test_dashboard_uses_measurement_drill_down_not_embedded_sparkline(self) -> None:
        dashboard = Path(
            "clients/android/app/src/main/java/nz/farmpi/client/DashboardVisuals.kt"
        ).read_text(encoding="utf-8")
        monitoring = Path(
            "clients/android/app/src/main/java/nz/farmpi/client/MonitoringUi.kt"
        ).read_text(encoding="utf-8")

        self.assertNotIn("MiniSparkline", dashboard)
        self.assertIn("View trend", dashboard)
        self.assertIn("HISTORY_MEASUREMENTS", monitoring)
        self.assertIn('listOf("6 hours", "1 day", "7 days")', monitoring)
        self.assertNotIn('Text("Recent trend"', monitoring)


if __name__ == "__main__":
    unittest.main()
