-- Repeatable synthetic baseline and upgrade for the 16-paddock simulation.
-- The sensor UID is the stable identity. Existing nodes keep their current
-- paddock_id, so reapplying this file after "Paddock A" has been renamed to
-- "North Flat" cannot recreate Paddock A or move test-moisture-a away from it.
INSERT INTO paddocks (name, active)
SELECT v.paddock_name, TRUE
FROM (
 SELECT 'a' suffix, 'Paddock A' paddock_name UNION ALL
 SELECT 'b', 'Paddock B' UNION ALL
 SELECT 'c', 'Paddock C' UNION ALL
 SELECT 'd', 'Paddock D' UNION ALL
 SELECT 'e', 'Paddock E' UNION ALL
 SELECT 'f', 'Paddock F' UNION ALL
 SELECT 'g', 'Paddock G' UNION ALL
 SELECT 'h', 'Paddock H' UNION ALL
 SELECT 'i', 'Paddock I' UNION ALL
 SELECT 'j', 'Paddock J' UNION ALL
 SELECT 'k', 'Paddock K' UNION ALL
 SELECT 'l', 'Paddock L' UNION ALL
 SELECT 'm', 'Paddock M' UNION ALL
 SELECT 'n', 'Paddock N' UNION ALL
 SELECT 'o', 'Paddock O' UNION ALL
 SELECT 'p', 'Paddock P'
) AS v
LEFT JOIN sensor_nodes AS s ON s.node_uid = CONCAT('test-moisture-', v.suffix)
LEFT JOIN paddocks AS p ON p.name = v.paddock_name
WHERE s.id IS NULL AND p.id IS NULL
ON DUPLICATE KEY UPDATE active = VALUES(active);

INSERT INTO sensor_nodes (paddock_id, node_uid, name, active)
SELECT p.id, CONCAT('test-moisture-', v.suffix), CONCAT(v.paddock_name, ' virtual node'), TRUE
FROM (
 SELECT 'a' suffix, 'Paddock A' paddock_name UNION ALL
 SELECT 'b', 'Paddock B' UNION ALL
 SELECT 'c', 'Paddock C' UNION ALL
 SELECT 'd', 'Paddock D' UNION ALL
 SELECT 'e', 'Paddock E' UNION ALL
 SELECT 'f', 'Paddock F' UNION ALL
 SELECT 'g', 'Paddock G' UNION ALL
 SELECT 'h', 'Paddock H' UNION ALL
 SELECT 'i', 'Paddock I' UNION ALL
 SELECT 'j', 'Paddock J' UNION ALL
 SELECT 'k', 'Paddock K' UNION ALL
 SELECT 'l', 'Paddock L' UNION ALL
 SELECT 'm', 'Paddock M' UNION ALL
 SELECT 'n', 'Paddock N' UNION ALL
 SELECT 'o', 'Paddock O' UNION ALL
 SELECT 'p', 'Paddock P'
) AS v
JOIN paddocks AS p ON p.name = v.paddock_name
LEFT JOIN sensor_nodes AS s ON s.node_uid = CONCAT('test-moisture-', v.suffix)
WHERE s.id IS NULL
ON DUPLICATE KEY UPDATE active = VALUES(active);

-- An expected UID which already exists remains attached to its numeric
-- paddock identity. Reactivate it and make its descriptive node name follow
-- the paddock's current display name.
UPDATE sensor_nodes AS s
JOIN paddocks AS p ON p.id = s.paddock_id
SET s.name = CONCAT(p.name, ' virtual node'), s.active = TRUE, p.active = TRUE
WHERE s.node_uid REGEXP '^test-moisture-[a-p]$';

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
 pasture_height_cm, leaf_wetness_pct, simulated, observed_at, received_at,
 recorded_at, clock_valid, clock_offset_seconds, clock_out_of_tolerance,
 sample_seq, protocol_version
)
SELECT s.id, v.moisture, v.soil_temp, v.air_temp, v.humidity, v.ph, v.ec,
       v.lux, v.rain, v.pressure, v.wind_speed, v.wind_direction,
       v.height, v.leaf_wetness, TRUE,
       '2026-01-01 00:00:00.000000', '2026-01-01 00:00:00.000000',
       '2026-01-01 00:00:00.000000', FALSE, NULL, TRUE, NULL, 1
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
 simulated=VALUES(simulated), observed_at=VALUES(observed_at),
 received_at=VALUES(received_at), clock_valid=VALUES(clock_valid),
 clock_offset_seconds=VALUES(clock_offset_seconds),
 clock_out_of_tolerance=VALUES(clock_out_of_tolerance), protocol_version=VALUES(protocol_version);
