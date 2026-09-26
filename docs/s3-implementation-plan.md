# ESP32-S3 registration and configuration block

Inspection baseline: `da6a109671ff9f5ce43dc3339ab256e0954d4e0d`, from `F:/FarmPi`, 26 September 2026. Work takes place in an isolated checkout; staged Android icon work in the original checkout is not part of this change.

## Existing owners and smallest change set

* `firmware/esp32-sensor/esp32-sensor.ino`: currently the explicitly simulated 16-paddock generator. Retain this evaluation tool; introduce the physical S3 target alongside it, sharing the existing HTTP ingest contract rather than creating a second ingestion system.
* `app/measurements.py`: authoritative 13-measurement catalogue, including units and ranges. Reuse its keys; remove the six-baseline requirement from ingestion, not the six-physical-measurement acceptance requirement.
* `app/ingest_api.py`, `app/sensor_ingest.py`: extend existing validation and sparse storage. The inspected revision requires six values, not all 13 as described in the earlier development record.
* `config/database/schema.sql`, `app/database.py`: extend `sensor_nodes`, retain nullable wide `readings`, snapshot location on observations, and use transactions for node mutations. SQL NULL represents absence of a column value, not an invented measurement; absent values never enter the measurement map.
* `app/farm_data.py`: remove complete-baseline filtering and preserve observation location in historical queries.
* `clients/android/.../MainActivity.kt`: existing Compose app and HTTPS client, no existing node management screen. Extend its navigation and API helper with a dedicated Nodes screen.

## Protocol and integrity

Hardware UID, assigned node UID and location are separate. Discovery does not approve registration. Registration starts with no enabled measurements. Catalogue, configurable capabilities and actual physical acquisition remain distinct: the soil-moisture configuration path can be tested without claiming a driver exists or producing a value.

Use SHA-256 over an exact canonical complete configuration document, with numeric schema_version. Full hash is authoritative; display eight hexadecimal characters. Poll at boot and normal contact, fetch only latest complete state, validate before replacing NVS, apply then acknowledge. Record failures against their attempted fingerprint so an obsolete failure cannot mark a newer desired configuration failed.

Keep current ingest bearer authentication for legacy simulation. Hardware UID is identification, not a secret; managed physical nodes need a per-device secret and administrative approval. Management uses an explicit administrator token. Record exact build and dependency versions, tests, failures and unresolved hardware checks.

## Evidence and acceptance

Jeremy corrected the proposal to hard-code six physical values: each node must be configurable across the existing 13-measurement catalogue. Jeremy also challenged an increasing human-facing revision counter, leading to latest-state configuration fingerprint synchronisation with a separate schema version. Preserve subsequent material corrections in the development record.

Test two discoveries/registrations, all-disabled initial state, per-node isolation, hash stability/mismatch, latest-state application and stale acknowledgement handling, rejected configuration retaining working state, sparse telemetry, disabled/unsupported measurements, provenance, retry/time semantics and history location preservation. Hardware tests must separately cover two real S3s, reboots and unavailable FarmPi. T01 remains pending until all six FR01 physical measurements and FR02 identity/provenance are demonstrated. Exact probe electronics and final board pin assignments require the actual board and probe identification.
