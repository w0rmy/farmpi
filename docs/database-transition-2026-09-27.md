# Operational database and managed-node transition — 27 September 2026

## Why this transition exists

The early FarmPi prototype used a repeatable 16-location synthetic dataset. That was useful for application, graph, analytics and conversational testing, but it became a poor default once real managed ESP32-S3 nodes were introduced.

Jeremy identified the transition risk: leaving the old synthetic locations and rows in the normal operational database could make the application appear healthier or more complete than the real deployment, blur simulated and physical provenance, and keep earlier simulator assumptions embedded in the new node model.

The decision is therefore to preserve the old simulator as an explicit test/demo tool while making the normal operational database clean and managed-node first.

## Database policy

Normal setup and schema updates now apply schema only. They do not automatically load the 16-location demo seed.

To load the old demonstration dataset deliberately:

```bash
sudo bash scripts/load-demo-data
```

To transition an existing installation to a clean operational database:

```bash
sudo bash scripts/reset-operational-database --yes
```

The reset helper:

1. stops FarmPi if installed;
2. creates a timestamped full SQL backup and schema-only backup under `/var/backups/farmpi`;
3. drops and recreates the `farmpi` database;
4. applies the current schema without synthetic seed data;
5. restarts FarmPi;
6. leaves existing ESP32-S3 NVS device credentials untouched, so the real boards rediscover as pending and can be approved again.

This destructive reset is explicit. Pulling code or running the normal update path does not delete operational data.

## Identity and location

FarmPi now keeps three different concepts separate:

- **hardware UID** — immutable ESP32 hardware identity;
- **logical FarmPi node ID** — stable support identity such as `FP-001`;
- **location display name** — farmer-defined and editable, such as `Bob's`, `Back Hill` or `Down by the Trough`.

A node may move to another location without changing its hardware or logical identity. Multiple nodes can later share one location because location remains a separate database entity.

The node's optional friendly name is also separate from location, for example `Gate sensor` or `Weather post`.

## Per-measurement operating modes

Managed-node configuration schema version 2 replaces the earlier enabled/disabled list with one explicit mode per supported measurement:

- `OFF` — do not acquire or transmit the measurement;
- `SIMULATED` — generate the value on the ESP32 and send it through the real managed-node telemetry path;
- `LIVE` — acquire the value through an implemented and tested physical driver.

A firmware profile advertises two capability sets:

- measurements it can configure/simulate;
- measurements for which a real LIVE acquisition driver is actually available.

The current ESP32-S3 profile can simulate all 13 catalogue measurements but advertises no LIVE measurement yet. This prevents the UI/server from claiming physical acquisition before a driver exists.

## Provenance

Simulation has moved to the sensor-driver boundary rather than the database/backend.

The ESP32 splits SIMULATED and LIVE values into separate sparse telemetry requests. The existing per-reading `simulated` flag therefore remains exact even on a node that later mixes simulated and physical measurements.

FarmPi validates every supplied measurement against the node's acknowledged desired/applied mode before storage. OFF, stale/unapplied, unsupported or wrong-provenance submissions are rejected.

## Android node administration

The main Nodes page remains a compact list.

Farmer-facing location names are shown first. Technical identity is secondary.

Opening a node shows its own detail page, where the administrator can:

- set a friendly node name;
- choose an existing location or enter a farmer-defined location name;
- inspect each supported measurement's current OFF, SIMULATED or LIVE state;
- inspect technical identity, firmware and configuration fingerprints.

During the prototype, source-mode changes are deliberately made from the FarmPi console rather than the farmer-facing Android UI. Use `.venv/bin/python scripts/configure-node-modes`. LIVE is rejected unless firmware explicitly advertises a tested live driver.

## Evidence significance

This transition is retained as capstone evidence rather than hidden as cleanup.

The earlier simulator was appropriate for its development stage. The issue appeared only after the application changed from a simulation-led prototype to managed real nodes. Jeremy identified that carrying the old synthetic operational state forward would create ambiguity, proposed a clean database baseline, moved simulation into the real ESP32 acquisition boundary, and separated farmer location naming from node identity.

That change is evidence of requirements reinterpretation, architecture evolution, provenance control, scope judgement and human review of AI proposals.
