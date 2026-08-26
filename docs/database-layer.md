# FarmPi deterministic MariaDB layer

The model has no MariaDB credentials or SQL path. app/database.py is the connection boundary; app/measurements.py is the reviewed schema/operation catalogue; app/farm_data.py computes current and limited historical facts.

## Data model and migration

paddocks holds mutable display names, sensor_nodes assigns a stable UID to a paddock, and readings holds timestamped telemetry. Readings always reference sensor_nodes.id, which references paddocks.id. Renaming a display name never rewrites history. The readings migration now separates `observed_at`, `received_at`, and `created_at`; see [time-sync-telemetry.md](time-sync-telemetry.md) for the deliberate current/historical query choice and sequence deduplication.

schema.sql is additive for existing alpha installs: new readings columns are nullable so older five-field rows remain valid, while new API writes are complete. New installations receive range CHECK constraints; schema reapplication adds missing columns and checks where MariaDB supports idempotent ADD CONSTRAINT IF NOT EXISTS.

seed.sql is also a repeatable deployment migration. It expands an original four-node database to 16 active virtual sensor UIDs and supplies one old complete synthetic baseline per node. Sensor UID, rather than the default display name, is the stable migration identity. If Paddock A has already become North Flat, reapplying the seed retains test-moisture-a's existing paddock_id and updates only its descriptive node name. It neither recreates Paddock A nor moves historical readings. `./update` applies both schema.sql and seed.sql whenever the configured MariaDB service is present.

paddock_admin_audit records paddock_id, old_name, new_name, action, and created_at. It is an evidence trail for controlled mutation.

## Deterministic operations

The latest-complete reading query uses `received_at` for current values/freshness. Historical queries deliberately use valid, in-tolerance `observed_at`, falling back to `received_at` for invalid/drifted clocks. They remain intentionally small: a bounded 5-minute-to-7-day window can provide permitted sum, minimum, maximum, average or last-minus-first change.

Derived daylight counts each five-minute historical light sample at or above 1,000 lux. It is documented approximation, not a stored field and not an LLM calculation.

The prior “Paddock IS” failure is guarded by treating conversational words after paddock as non-identifiers. For arbitrary current names, the router extracts only a candidate phrase and the data layer resolves it against the database names; it does not hard-code Paddock A/B/C.
# Current implementation note

Analytics selects an explicit UTC range. Local-calendar requests such as `today` are first converted from `Pacific/Auckland` midnight to UTC, avoiding the common error of presenting a rolling 24-hour window as a local day. It uses valid, in-tolerance `observed_at`; otherwise it uses FarmPi `received_at`. See [analytics and graphing](analytics-and-graphing.md).
