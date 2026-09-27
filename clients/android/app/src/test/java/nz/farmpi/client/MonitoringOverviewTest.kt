package nz.farmpi.client

import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test

class MonitoringOverviewTest {
    @Test
    fun overviewParsesMeasurementsLocationsAndFeaturedChart() {
        val json = JSONObject(
            """
            {
              "location_count": 2,
              "locations_with_readings_count": 1,
              "farm_measurements": [
                {
                  "key": "soil_moisture_pct",
                  "label": "soil moisture",
                  "unit": "%",
                  "value": 31.4,
                  "display_value": "31.40%",
                  "source_mode": "SIMULATED",
                  "age_seconds": 90,
                  "reporting_locations": 1
                }
              ],
              "locations": [
                {
                  "id": 1,
                  "name": "Bob's",
                  "active_sensor_count": 1,
                  "has_reading": true,
                  "age_seconds": 90,
                  "contains_simulated": true,
                  "measurements": [
                    {
                      "key": "soil_moisture_pct",
                      "label": "soil moisture",
                      "unit": "%",
                      "value": 31.4,
                      "display_value": "31.40%",
                      "source_mode": "SIMULATED",
                      "age_seconds": 90
                    }
                  ]
                }
              ],
              "featured_chart": {
                "type": "line",
                "title": "Soil moisture",
                "unit": "%",
                "source_period": "last 24 hours",
                "provenance": "verified",
                "series": [
                  {
                    "name": "Farm average",
                    "data": [
                      {"x": "12:00", "y": 30.0},
                      {"x": "13:00", "y": 31.4}
                    ]
                  }
                ]
              }
            }
            """.trimIndent()
        )

        val overview = json.monitoringOverview()

        assertEquals(2, overview.locationCount)
        assertEquals(1, overview.locationsWithReadingsCount)
        assertEquals("31.40%", overview.farmMeasurements.single().displayValue)
        assertEquals("Bob's", overview.locations.single().name)
        assertTrue(overview.locations.single().hasReading)
        assertEquals(2, overview.featuredChart?.series?.single()?.second?.size)
    }

    @Test
    fun ageLabelsDoNotPretendToClassifyConnectivity() {
        assertEquals("No current reading", ageLabel(null))
        assertEquals("Updated just now", ageLabel(20))
        assertEquals("Updated 2 min ago", ageLabel(120))
        assertEquals("Updated 2 h ago", ageLabel(7200))
    }
}
