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
    CONSTRAINT fk_sensor_nodes_paddock FOREIGN KEY (paddock_id) REFERENCES paddocks(id)
        ON UPDATE CASCADE ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS readings (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    sensor_node_id INT UNSIGNED NOT NULL,
    soil_moisture_pct DECIMAL(5,2) NULL,
    soil_temperature_c DECIMAL(5,2) NULL,
    air_temperature_c DECIMAL(5,2) NULL,
    relative_humidity_pct DECIMAL(5,2) NULL,
    soil_ph DECIMAL(4,2) NULL,
    soil_ec_ms_cm DECIMAL(5,2) NULL,
    light_lux DECIMAL(8,2) NULL,
    rainfall_mm DECIMAL(5,2) NULL,
    barometric_pressure_hpa DECIMAL(6,1) NULL,
    wind_speed_kmh DECIMAL(5,1) NULL,
    wind_direction_deg DECIMAL(5,0) NULL,
    pasture_height_cm DECIMAL(5,1) NULL,
    leaf_wetness_pct DECIMAL(5,1) NULL,
    simulated BOOLEAN NOT NULL DEFAULT FALSE,
    -- All DATETIME values use the FarmPi application UTC convention.
    -- recorded_at remains as an alpha compatibility/audit alias for received_at.
    observed_at DATETIME(6) NOT NULL,
    received_at DATETIME(6) NOT NULL,
    recorded_at DATETIME(6) NOT NULL,
    clock_valid BOOLEAN NOT NULL DEFAULT FALSE,
    clock_offset_seconds DECIMAL(10,3) NULL,
    clock_out_of_tolerance BOOLEAN NOT NULL DEFAULT TRUE,
    sample_seq BIGINT UNSIGNED NULL,
    protocol_version SMALLINT UNSIGNED NOT NULL DEFAULT 1,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_readings_sensor_time (sensor_node_id, recorded_at),
    UNIQUE KEY uq_readings_sensor_sample_seq (sensor_node_id, sample_seq),
    KEY idx_readings_sensor_recorded (sensor_node_id, recorded_at),
    KEY idx_readings_sensor_received (sensor_node_id, received_at),
    KEY idx_readings_sensor_observed (sensor_node_id, observed_at),
    CONSTRAINT fk_readings_sensor_node FOREIGN KEY (sensor_node_id) REFERENCES sensor_nodes(id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT chk_readings_soil_moisture CHECK (soil_moisture_pct IS NULL OR soil_moisture_pct BETWEEN 0 AND 100),
    CONSTRAINT chk_readings_soil_temperature CHECK (soil_temperature_c IS NULL OR soil_temperature_c BETWEEN -10 AND 60),
    CONSTRAINT chk_readings_air_temperature CHECK (air_temperature_c IS NULL OR air_temperature_c BETWEEN -30 AND 60),
    CONSTRAINT chk_readings_relative_humidity CHECK (relative_humidity_pct IS NULL OR relative_humidity_pct BETWEEN 0 AND 100),
    CONSTRAINT chk_readings_soil_ph CHECK (soil_ph IS NULL OR soil_ph BETWEEN 0 AND 14),
    CONSTRAINT chk_readings_soil_ec CHECK (soil_ec_ms_cm IS NULL OR soil_ec_ms_cm BETWEEN 0 AND 20),
    CONSTRAINT chk_readings_light_lux CHECK (light_lux IS NULL OR light_lux BETWEEN 0 AND 200000),
    CONSTRAINT chk_readings_rainfall CHECK (rainfall_mm IS NULL OR rainfall_mm BETWEEN 0 AND 100),
    CONSTRAINT chk_readings_pressure CHECK (barometric_pressure_hpa IS NULL OR barometric_pressure_hpa BETWEEN 850 AND 1100),
    CONSTRAINT chk_readings_wind_speed CHECK (wind_speed_kmh IS NULL OR wind_speed_kmh BETWEEN 0 AND 250),
    CONSTRAINT chk_readings_wind_direction CHECK (wind_direction_deg IS NULL OR wind_direction_deg BETWEEN 0 AND 360),
    CONSTRAINT chk_readings_pasture_height CHECK (pasture_height_cm IS NULL OR pasture_height_cm BETWEEN 0 AND 300),
    CONSTRAINT chk_readings_leaf_wetness CHECK (leaf_wetness_pct IS NULL OR leaf_wetness_pct BETWEEN 0 AND 100)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Additive migration path for existing alpha installations. Nullable columns
-- preserve older rows; new API payloads are complete and range-validated.
ALTER TABLE readings ADD COLUMN IF NOT EXISTS simulated BOOLEAN NOT NULL DEFAULT FALSE AFTER soil_moisture_pct;
ALTER TABLE readings ADD COLUMN IF NOT EXISTS soil_temperature_c DECIMAL(5,2) NULL AFTER soil_moisture_pct;
ALTER TABLE readings ADD COLUMN IF NOT EXISTS air_temperature_c DECIMAL(5,2) NULL AFTER soil_temperature_c;
ALTER TABLE readings ADD COLUMN IF NOT EXISTS relative_humidity_pct DECIMAL(5,2) NULL AFTER air_temperature_c;
ALTER TABLE readings ADD COLUMN IF NOT EXISTS soil_ph DECIMAL(4,2) NULL AFTER relative_humidity_pct;
ALTER TABLE readings ADD COLUMN IF NOT EXISTS soil_ec_ms_cm DECIMAL(5,2) NULL AFTER soil_ph;
ALTER TABLE readings ADD COLUMN IF NOT EXISTS light_lux DECIMAL(8,2) NULL AFTER soil_ec_ms_cm;
ALTER TABLE readings ADD COLUMN IF NOT EXISTS rainfall_mm DECIMAL(5,2) NULL AFTER light_lux;
ALTER TABLE readings ADD COLUMN IF NOT EXISTS barometric_pressure_hpa DECIMAL(6,1) NULL AFTER rainfall_mm;
ALTER TABLE readings ADD COLUMN IF NOT EXISTS wind_speed_kmh DECIMAL(5,1) NULL AFTER barometric_pressure_hpa;
ALTER TABLE readings ADD COLUMN IF NOT EXISTS wind_direction_deg DECIMAL(5,0) NULL AFTER wind_speed_kmh;
ALTER TABLE readings ADD COLUMN IF NOT EXISTS pasture_height_cm DECIMAL(5,1) NULL AFTER wind_direction_deg;
ALTER TABLE readings ADD COLUMN IF NOT EXISTS leaf_wetness_pct DECIMAL(5,1) NULL AFTER pasture_height_cm;
ALTER TABLE readings ADD COLUMN IF NOT EXISTS observed_at DATETIME(6) NULL AFTER simulated;
ALTER TABLE readings ADD COLUMN IF NOT EXISTS received_at DATETIME(6) NULL AFTER observed_at;
ALTER TABLE readings ADD COLUMN IF NOT EXISTS clock_valid BOOLEAN NOT NULL DEFAULT FALSE AFTER received_at;
ALTER TABLE readings ADD COLUMN IF NOT EXISTS clock_offset_seconds DECIMAL(10,3) NULL AFTER clock_valid;
ALTER TABLE readings ADD COLUMN IF NOT EXISTS clock_out_of_tolerance BOOLEAN NOT NULL DEFAULT TRUE AFTER clock_offset_seconds;
ALTER TABLE readings ADD COLUMN IF NOT EXISTS sample_seq BIGINT UNSIGNED NULL AFTER clock_out_of_tolerance;
ALTER TABLE readings ADD COLUMN IF NOT EXISTS protocol_version SMALLINT UNSIGNED NOT NULL DEFAULT 1 AFTER sample_seq;

-- Safe backfill for alpha rows. Their old server timestamp is both the
-- receive time and the only trustworthy observation-time fallback.
UPDATE readings
SET observed_at = COALESCE(observed_at, recorded_at),
    received_at = COALESCE(received_at, recorded_at)
WHERE observed_at IS NULL OR received_at IS NULL;

ALTER TABLE readings ADD UNIQUE INDEX IF NOT EXISTS uq_readings_sensor_sample_seq (sensor_node_id, sample_seq);
ALTER TABLE readings ADD INDEX IF NOT EXISTS idx_readings_sensor_received (sensor_node_id, received_at);
ALTER TABLE readings ADD INDEX IF NOT EXISTS idx_readings_sensor_observed (sensor_node_id, observed_at);

-- MariaDB 10.5+ accepts IF NOT EXISTS for constraints. If a much older
-- installation rejects this syntax, the harmless fallback is to retain API
-- validation and add the named checks once during the upgrade.
ALTER TABLE readings ADD CONSTRAINT IF NOT EXISTS chk_readings_soil_temperature CHECK (soil_temperature_c IS NULL OR soil_temperature_c BETWEEN -10 AND 60);
ALTER TABLE readings ADD CONSTRAINT IF NOT EXISTS chk_readings_soil_ec CHECK (soil_ec_ms_cm IS NULL OR soil_ec_ms_cm BETWEEN 0 AND 20);
ALTER TABLE readings ADD CONSTRAINT IF NOT EXISTS chk_readings_rainfall CHECK (rainfall_mm IS NULL OR rainfall_mm BETWEEN 0 AND 100);
ALTER TABLE readings ADD CONSTRAINT IF NOT EXISTS chk_readings_pressure CHECK (barometric_pressure_hpa IS NULL OR barometric_pressure_hpa BETWEEN 850 AND 1100);
ALTER TABLE readings ADD CONSTRAINT IF NOT EXISTS chk_readings_wind_speed CHECK (wind_speed_kmh IS NULL OR wind_speed_kmh BETWEEN 0 AND 250);
ALTER TABLE readings ADD CONSTRAINT IF NOT EXISTS chk_readings_wind_direction CHECK (wind_direction_deg IS NULL OR wind_direction_deg BETWEEN 0 AND 360);
ALTER TABLE readings ADD CONSTRAINT IF NOT EXISTS chk_readings_pasture_height CHECK (pasture_height_cm IS NULL OR pasture_height_cm BETWEEN 0 AND 300);
ALTER TABLE readings ADD CONSTRAINT IF NOT EXISTS chk_readings_leaf_wetness CHECK (leaf_wetness_pct IS NULL OR leaf_wetness_pct BETWEEN 0 AND 100);

CREATE TABLE IF NOT EXISTS paddock_admin_audit (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    paddock_id INT UNSIGNED NOT NULL,
    old_name VARCHAR(100) NOT NULL,
    new_name VARCHAR(100) NOT NULL,
    action VARCHAR(32) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY idx_paddock_admin_audit_paddock_time (paddock_id, created_at),
    CONSTRAINT fk_paddock_admin_audit_paddock FOREIGN KEY (paddock_id) REFERENCES paddocks(id)
        ON UPDATE CASCADE ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
