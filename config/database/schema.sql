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
        CHECK (soil_moisture_pct IS NULL OR (soil_moisture_pct >= 0 AND soil_moisture_pct <= 100))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
