-- Repeatable prototype data. These are not live farm readings.
-- The fixed timestamp keeps this seed idempotent through the unique
-- (sensor_node_id, recorded_at) key.

INSERT INTO paddocks (name, active) VALUES
    ('Paddock A', TRUE),
    ('Paddock B', TRUE),
    ('Paddock C', TRUE),
    ('Paddock D', TRUE)
ON DUPLICATE KEY UPDATE active = VALUES(active);

INSERT INTO sensor_nodes (paddock_id, node_uid, name, active)
SELECT id, 'test-moisture-a', 'Paddock A moisture sensor', TRUE
FROM paddocks WHERE name = 'Paddock A'
ON DUPLICATE KEY UPDATE paddock_id = VALUES(paddock_id), name = VALUES(name), active = VALUES(active);

INSERT INTO sensor_nodes (paddock_id, node_uid, name, active)
SELECT id, 'test-moisture-b', 'Paddock B moisture sensor', TRUE
FROM paddocks WHERE name = 'Paddock B'
ON DUPLICATE KEY UPDATE paddock_id = VALUES(paddock_id), name = VALUES(name), active = VALUES(active);

INSERT INTO sensor_nodes (paddock_id, node_uid, name, active)
SELECT id, 'test-moisture-c', 'Paddock C moisture sensor', TRUE
FROM paddocks WHERE name = 'Paddock C'
ON DUPLICATE KEY UPDATE paddock_id = VALUES(paddock_id), name = VALUES(name), active = VALUES(active);

INSERT INTO sensor_nodes (paddock_id, node_uid, name, active)
SELECT id, 'test-moisture-d', 'Paddock D moisture sensor', TRUE
FROM paddocks WHERE name = 'Paddock D'
ON DUPLICATE KEY UPDATE paddock_id = VALUES(paddock_id), name = VALUES(name), active = VALUES(active);

INSERT INTO readings (sensor_node_id, soil_moisture_pct, simulated, recorded_at)
SELECT id, 18.00, TRUE, '2026-08-26 18:00:00.000000'
FROM sensor_nodes WHERE node_uid = 'test-moisture-a'
ON DUPLICATE KEY UPDATE
    soil_moisture_pct = VALUES(soil_moisture_pct),
    simulated = VALUES(simulated);

INSERT INTO readings (sensor_node_id, soil_moisture_pct, simulated, recorded_at)
SELECT id, 24.00, TRUE, '2026-08-26 18:00:00.000000'
FROM sensor_nodes WHERE node_uid = 'test-moisture-b'
ON DUPLICATE KEY UPDATE
    soil_moisture_pct = VALUES(soil_moisture_pct),
    simulated = VALUES(simulated);

INSERT INTO readings (sensor_node_id, soil_moisture_pct, simulated, recorded_at)
SELECT id, 29.00, TRUE, '2026-08-26 18:00:00.000000'
FROM sensor_nodes WHERE node_uid = 'test-moisture-c'
ON DUPLICATE KEY UPDATE
    soil_moisture_pct = VALUES(soil_moisture_pct),
    simulated = VALUES(simulated);

INSERT INTO readings (sensor_node_id, soil_moisture_pct, simulated, recorded_at)
SELECT id, 21.00, TRUE, '2026-08-26 18:00:00.000000'
FROM sensor_nodes WHERE node_uid = 'test-moisture-d'
ON DUPLICATE KEY UPDATE
    soil_moisture_pct = VALUES(soil_moisture_pct),
    simulated = VALUES(simulated);
