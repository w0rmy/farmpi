-- Repeatable synthetic baseline for the 16-paddock alpha simulation.
-- Names are display values only: readings link through paddocks.id and
-- sensor_nodes.id, so later renames do not rewrite or orphan history.
INSERT INTO paddocks (name, active) VALUES
('Paddock A', TRUE), ('Paddock B', TRUE), ('Paddock C', TRUE), ('Paddock D', TRUE),
('Paddock E', TRUE), ('Paddock F', TRUE), ('Paddock G', TRUE), ('Paddock H', TRUE),
('Paddock I', TRUE), ('Paddock J', TRUE), ('Paddock K', TRUE), ('Paddock L', TRUE),
('Paddock M', TRUE), ('Paddock N', TRUE), ('Paddock O', TRUE), ('Paddock P', TRUE)
ON DUPLICATE KEY UPDATE active = VALUES(active);

INSERT INTO sensor_nodes (paddock_id, node_uid, name, active)
SELECT p.id, CONCAT('test-moisture-', LOWER(RIGHT(p.name, 1))), CONCAT(p.name, ' virtual node'), TRUE
FROM paddocks AS p
WHERE p.name REGEXP '^Paddock [A-P]$'
ON DUPLICATE KEY UPDATE paddock_id = VALUES(paddock_id), name = VALUES(name), active = VALUES(active);

-- Remove the alpha seed timestamp that was accidentally later than UTC ingest
-- timestamps on some New Zealand installations.
DELETE r FROM readings AS r
JOIN sensor_nodes AS s ON s.id = r.sensor_node_id
WHERE s.node_uid REGEXP '^test-moisture-[a-p]$'
  AND r.recorded_at = '2026-08-26 18:00:00.000000';

-- Old, complete, server-UTC baseline. Real/synthetic ingest always supersedes
-- it, while making a clean install queryable before the first ESP32 round.
INSERT INTO readings (
 sensor_node_id, soil_moisture_pct, soil_temperature_c, air_temperature_c,
 relative_humidity_pct, soil_ph, soil_ec_ms_cm, light_lux, rainfall_mm,
 barometric_pressure_hpa, wind_speed_kmh, wind_direction_deg,
 pasture_height_cm, leaf_wetness_pct, simulated, recorded_at
)
SELECT s.id, v.moisture, v.soil_temp, v.air_temp, v.humidity, v.ph, v.ec,
       v.lux, v.rain, v.pressure, v.wind_speed, v.wind_direction,
       v.height, v.leaf_wetness, TRUE, '2026-01-01 00:00:00.000000'
FROM sensor_nodes AS s
JOIN (
 SELECT 'a' suffix, 18.0 moisture, 13.2 soil_temp, 16.5 air_temp, 74.0 humidity, 6.2 ph, 0.42 ec, 12000 lux, 0.0 rain, 1015.2 pressure, 9.0 wind_speed, 225 wind_direction, 10.5 height, 8.0 leaf_wetness UNION ALL
 SELECT 'b', 24.0, 14.0, 17.2, 69.0, 6.5, 0.55, 14500, 0.0, 1015.2, 9.0, 225, 13.0, 6.0 UNION ALL
 SELECT 'c', 29.0, 14.8, 18.1, 64.0, 6.7, 0.61, 16200, 0.0, 1015.2, 9.0, 225, 11.5, 5.0 UNION ALL
 SELECT 'd', 21.0, 12.8, 15.7, 78.0, 6.1, 0.38, 9800, 0.0, 1015.2, 9.0, 225, 15.0, 10.0 UNION ALL
 SELECT 'e', 16.0, 12.0, 16.0, 72.0, 6.3, 0.48, 10500, 0.0, 1015.2, 9.0, 225, 9.0, 7.0 UNION ALL
 SELECT 'f', 31.0, 14.5, 17.5, 70.0, 6.6, 0.67, 13800, 0.0, 1015.2, 9.0, 225, 16.0, 9.0 UNION ALL
 SELECT 'g', 20.0, 13.0, 16.2, 76.0, 5.9, 0.35, 8800, 0.0, 1015.2, 9.0, 225, 12.0, 11.0 UNION ALL
 SELECT 'h', 26.0, 14.3, 17.0, 68.0, 6.4, 0.58, 15300, 0.0, 1015.2, 9.0, 225, 14.0, 5.0 UNION ALL
 SELECT 'i', 23.0, 13.8, 16.8, 71.0, 6.2, 0.46, 11300, 0.0, 1015.2, 9.0, 225, 10.0, 8.0 UNION ALL
 SELECT 'j', 28.0, 14.6, 17.8, 66.0, 6.8, 0.70, 16800, 0.0, 1015.2, 9.0, 225, 17.5, 4.0 UNION ALL
 SELECT 'k', 19.0, 12.9, 15.9, 79.0, 6.0, 0.40, 9200, 0.0, 1015.2, 9.0, 225, 11.0, 12.0 UNION ALL
 SELECT 'l', 25.0, 14.1, 17.1, 69.0, 6.5, 0.53, 14100, 0.0, 1015.2, 9.0, 225, 13.5, 6.0 UNION ALL
 SELECT 'm', 17.0, 12.4, 16.1, 75.0, 6.1, 0.37, 9700, 0.0, 1015.2, 9.0, 225, 8.5, 10.0 UNION ALL
 SELECT 'n', 30.0, 14.9, 18.0, 65.0, 6.7, 0.65, 16000, 0.0, 1015.2, 9.0, 225, 16.5, 5.0 UNION ALL
 SELECT 'o', 22.0, 13.6, 16.6, 73.0, 6.3, 0.50, 11000, 0.0, 1015.2, 9.0, 225, 12.5, 8.0 UNION ALL
 SELECT 'p', 27.0, 14.4, 17.6, 67.0, 6.6, 0.60, 15000, 0.0, 1015.2, 9.0, 225, 15.5, 6.0
) AS v ON s.node_uid = CONCAT('test-moisture-', v.suffix)
ON DUPLICATE KEY UPDATE
 soil_moisture_pct=VALUES(soil_moisture_pct), soil_temperature_c=VALUES(soil_temperature_c),
 air_temperature_c=VALUES(air_temperature_c), relative_humidity_pct=VALUES(relative_humidity_pct),
 soil_ph=VALUES(soil_ph), soil_ec_ms_cm=VALUES(soil_ec_ms_cm), light_lux=VALUES(light_lux),
 rainfall_mm=VALUES(rainfall_mm), barometric_pressure_hpa=VALUES(barometric_pressure_hpa),
 wind_speed_kmh=VALUES(wind_speed_kmh), wind_direction_deg=VALUES(wind_direction_deg),
 pasture_height_cm=VALUES(pasture_height_cm), leaf_wetness_pct=VALUES(leaf_wetness_pct),
 simulated=VALUES(simulated);
