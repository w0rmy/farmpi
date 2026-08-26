CREATE TABLE IF NOT EXISTS paddocks (
    id INT UNSIGNED NOT NULL AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_paddocks_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS sensor_nodes (
    id INT UNSIGNED NOT NULL AUTO_INCREMENT,
    paddock_id INT UNSIGNED NOT NULL,
    node_uid VARCHAR(64) NOT NULL,
    name VARCHAR(100) NOT NULL,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_sensor_nodes_uid (node_uid),
    KEY idx_sensor_nodes_paddock (paddock_id),
    CONSTRAINT fk_sensor_nodes_paddock
        FOREIGN KEY (paddock_id) REFERENCES paddocks(id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS readings (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    sensor_node_id INT UNSIGNED NOT NULL,
    soil_moisture_pct DECIMAL(5,2) NULL,
    air_temperature_c DECIMAL(5,2) NULL,
    relative_humidity_pct DECIMAL(5,2) NULL,
    soil_ph DECIMAL(4,2) NULL,
    light_lux DECIMAL(8,2) NULL,
    simulated BOOLEAN NOT NULL DEFAULT FALSE,
    recorded_at DATETIME(6) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_readings_sensor_time (sensor_node_id, recorded_at),
    KEY idx_readings_sensor_recorded (sensor_node_id, recorded_at),
    CONSTRAINT fk_readings_sensor_node
        FOREIGN KEY (sensor_node_id) REFERENCES sensor_nodes(id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,
    CONSTRAINT chk_readings_soil_moisture
        CHECK (soil_moisture_pct IS NULL OR (soil_moisture_pct >= 0 AND soil_moisture_pct <= 100)),
    CONSTRAINT chk_readings_air_temperature
        CHECK (air_temperature_c IS NULL OR (air_temperature_c >= -30 AND air_temperature_c <= 60)),
    CONSTRAINT chk_readings_relative_humidity
        CHECK (relative_humidity_pct IS NULL OR (relative_humidity_pct >= 0 AND relative_humidity_pct <= 100)),
    CONSTRAINT chk_readings_soil_ph
        CHECK (soil_ph IS NULL OR (soil_ph >= 0 AND soil_ph <= 14)),
    CONSTRAINT chk_readings_light_lux
        CHECK (light_lux IS NULL OR (light_lux >= 0 AND light_lux <= 200000))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Existing alpha databases may pre-date the simulated marker. MariaDB accepts
-- ADD COLUMN IF NOT EXISTS, making this schema safe to re-apply during updates.
ALTER TABLE readings
    ADD COLUMN IF NOT EXISTS simulated BOOLEAN NOT NULL DEFAULT FALSE
    AFTER soil_moisture_pct;

-- The nullable additions preserve any older, moisture-only alpha rows. New
-- /api/ingest payloads always provide all five instantaneous measurements.
ALTER TABLE readings
    ADD COLUMN IF NOT EXISTS air_temperature_c DECIMAL(5,2) NULL
    AFTER soil_moisture_pct;
ALTER TABLE readings
    ADD COLUMN IF NOT EXISTS relative_humidity_pct DECIMAL(5,2) NULL
    AFTER air_temperature_c;
ALTER TABLE readings
    ADD COLUMN IF NOT EXISTS soil_ph DECIMAL(4,2) NULL
    AFTER relative_humidity_pct;
ALTER TABLE readings
    ADD COLUMN IF NOT EXISTS light_lux DECIMAL(8,2) NULL
    AFTER soil_ph;
