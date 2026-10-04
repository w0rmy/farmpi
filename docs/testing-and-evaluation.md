# Testing, evaluation, and capstone evidence

FarmPi now needs evidence that the integrated application works as designed and that the implementation demonstrates the current electives: **Advanced Application Development Concepts** and **Artificial Intelligence and Data Science**.

The evaluation focus is therefore functional, architectural, integration-based, and evidence-led. Earlier learner/course evaluation remains historical work rather than the current primary acceptance target.

## Current capstone acceptance state — 3 October 2026

The current consolidated acceptance state is retained in [Capstone acceptance consolidation — 3 October 2026](evidence/capstone-acceptance-consolidation-2026-10-03.md).

| Check | State | Current evidence boundary |
|---|---|---|
| T01 — Physical sensing | **PARTIAL (1/6)** | XC4604 soil moisture is accepted end to end. Five required physical measurement channels remain undemonstrated. |
| T02 — Communication and freshness | **PASS** | Prior communication/freshness acceptance is project-owner/operator confirmed. This documentation update records closure without inventing a new raw transcript. |
| T03 — History and storage | **PASS** | Prior history/storage acceptance is project-owner/operator confirmed. This documentation update records closure without inventing additional raw evidence. |
| T04 — Thresholds and alerts | **DEFERRED** | FR06/FR07/T04 are future-release items, not current capstone completion criteria. |
| T05 — Analysis and AI grounding | **PASS / CLOSED** | Live authority-boundary acceptance, PR #47 known-value strengthening, PR #48 stale-test correction and the clean 192-test Pi regression result close the retained gaps. |
| T06 — Offline use and startup | **PASS — developer/operator acceptance** | Local/offline operation and resilience have been accepted; this does not replace comparative stakeholder usability evidence. |
| T07 — Maintainability and repeatability | **PASS** | FarmPi was successfully reinstalled onto a new Raspberry Pi SD card using the documented deployment approach. |

After the documentation-only reconciliation is merged, the resulting `main` is intended to be frozen as the stakeholder-test/capstone baseline. A later change is justified only by stakeholder findings, remaining T01 physical integration, or a genuine evidence/requirements contradiction.

## Automated backend checks

From the repository root, with the project virtual environment active:

```bash
python -m unittest discover -s tests -v
python -m compileall -q app tests
```

The suite should cover:

- measurement validation, natural-language aliases, and the standard-versus-optional capability catalogue;
- managed sparse telemetry ingest, capability/mode validation, per-measurement provenance, and optional/add-on values when supplied;
- telemetry time, sequence, deduplication, and ingest behaviour;
- database operations and paddock identity;
- current paddock summaries that omit unavailable optional measurements rather than inventing values;
- farm-wide optional analytics that use only paddocks reporting the requested capability;
- deterministic analytics and graph payloads;
- farm-wide versus named-paddock versus comparison semantics;
- rename confirmation and audit behaviour;
- speech normalisation;
- semantic interpretation and low-confidence recovery;
- source hierarchy and provenance;
- LLM compatibility and bounded conversation context;
- graceful fallback when the LLM or database is unavailable;
- Android/API contract assumptions that can be verified at the backend boundary.

Legacy course-contract tests may remain while that code exists, but they are regression coverage rather than current elective evidence.

Farm facts must be testable without an LLM. Current readings, history, comparisons, device state, timestamps, calculations, capability availability, and chart values must assert exact deterministic results and must not substitute generated text for database evidence.

## Sensor capability acceptance

FarmPi's application catalogue contains 13 reviewed measurements. The managed physical-node architecture does **not** require every node or every telemetry payload to contain the six FR01 physical measurements. Instead, firmware capability, per-node enablement and actual reporting state are tested separately.

Acceptance should include at minimum:

1. registration starts every advertised measurement in OFF mode;
2. a node may configure only measurements advertised by its firmware capability set;
3. OFF produces no reading and a supplied OFF/unsupported measurement is rejected;
4. SIMULATED produces bounded node-local test telemetry through the same authenticated path as later LIVE telemetry;
5. LIVE configuration and telemetry require an advertised physical driver; unsupported LIVE must be rejected, and an advertised driver that fails to read must not fabricate a value;
6. a nonempty sparse telemetry payload is accepted only when each supplied measurement matches the acknowledged configured mode;
7. omitted measurements remain absent/SQL `NULL` and are never converted into fabricated zeroes or placeholders;
8. per-measurement provenance survives ingest/storage and distinguishes SIMULATED from LIVE values;
9. invalid types, non-finite values and out-of-range supplied values are rejected;
10. retry/deduplication works for sparse payloads;
11. current location summaries show only measurements actually present in the selected observation;
12. direct requests for unavailable measurements say the location does not currently report them;
13. farm-wide analytics use only locations that actually report the requested measurement;
14. historical queries/graphs ignore rows where the requested measurement is `NULL`;
15. changing a sensor from SIMULATED to LIVE cannot reuse a recent simulated timestamp to appear as LIVE reporting;
16. per-node configuration changes are isolated: changing node A must not alter node B's desired/applied fingerprint or mode map;
17. farmer location assignment is separate from hardware/FarmPi identity, and moving a node preserves its historical readings at the old location.

Separately, **T01 final physical acceptance still requires all six FR01 measurements** - soil moisture, soil temperature, air temperature, relative humidity, light and barometric pressure - to be demonstrated from real hardware with correct source/location/time/units and physical-versus-simulated provenance. That requirement must not be implemented by forcing every intermediate node payload to contain all six values.

## Android acceptance checks

Build the debug client from `clients/android`:

```powershell
.\gradlew.bat :app:assembleDebug
```

Then test on a device that trusts the FarmPi development certificate.

Core acceptance areas:

- typed and spoken input;
- visible and spoken output;
- TTS stop/retry behaviour and null/blank spoken-answer fallback;
- connection/dependency status;
- current-value, historical, comparison, and graph requests;
- clear unavailable-capability wording when an optional sensor is not installed/reported;
- evidence/provenance display;
- settings persistence;
- portrait, landscape, and at least one small phone display;
- readable graph controls and chart labels;
- useful user-facing recovery when wording is unclear or a capability is unavailable;
- clear separation between network/certificate failures and valid FarmPi requests that could not be completed.

Graph acceptance should include at minimum:

1. `Can you show me the soil moisture over 24 hours?`
2. `Show me a light day profile graph.`
3. a named-paddock historical graph;
4. an explicit cross-paddock comparison;
5. an unsupported graph request;
6. a graph request for an optional measurement with no reporting data;
7. switching through every offered visual mode and confirming that values do not change.

A generic graph request must not invent a paddock name from phrases such as `the soil moisture over 24 hours` or `the lighting of the paddock`. The application should use farm-wide data when that is the appropriate supported meaning.

## Functional query acceptance

The following groups should be exercised as an end-to-end user journey:

- **Conversation continuity:** ask a question, then use pronouns or shorthand such as `explain that more simply` and `why does that matter?`.
- **Open information:** ask a farm question, an adjacent technical/agricultural question, and an unrelated safe informational question.
- **Provenance:** compare deterministic FarmPi data, reviewed source material, and model/general knowledge.
- **Deterministic consistency:** ask for the same farm value using several phrasings and confirm the number is identical.
- **Capability availability:** compare a six-sensor standard paddock with a paddock that also reports an optional add-on measurement.
- **Graphing:** test generic farm-wide, named-paddock, and explicit comparison requests.
- **Natural-language variation:** deliberately use colloquial, incomplete, or speech-like wording.
- **Failure/recovery:** stop the LLM, stop or deny database access, request a nonexistent paddock, and request unavailable data/capabilities.

User-facing failure text should not expose internal route names, SQL, `deterministic operation`, JSON, or model-server jargon unless diagnostic detail was explicitly requested.

## Raspberry Pi deployment checks

After install or update:

```bash
sudo systemctl is-active mariadb farmpi-llm farmpi caddy
curl -fsS http://127.0.0.1:8000/health
curl -fsS http://127.0.0.1:8000/api/status
curl --resolve farmpi.local:443:127.0.0.1 -k https://farmpi.local/health
```

Also exercise one registered managed-node contact/configuration cycle, submit one authenticated sparse physical test fixture for an enabled capability, retry the same sensor/sequence to confirm deduplication, verify disabled/unsupported values are rejected, ask for exact available and unavailable values, request a historical calculation and graph, test a broader general question, and verify that a stopped database or LLM is described honestly. Fixture telemetry must not be presented as physical probe evidence.

Do not record credentials in test output or evidence documents.

## Requirements traceability

Every material change should link implementation, verification, and capstone evidence:

| Concern | Required evidence |
|---|---|
| Functional requirement | working end-to-end behaviour plus acceptance result |
| Architecture | component/responsibility mapping and rationale |
| Farm facts and calculations | exact fixtures, provenance fields, failure-path tests |
| Sensor capability model | managed sparse ingest, OFF/SIMULATED/LIVE checks, per-measurement provenance, nullable storage, mixed-capability current/history behaviour |
| Mobile interface | device build/acceptance, layout/usability observations, state persistence |
| Graphing/analytics | deterministic value tests plus visual acceptance |
| AI interpretation | constrained schema tests, semantic recovery, no model authority over farm facts |
| Source/provenance | tier/category assertions and reviewed claim/source records |
| State-changing actions | validation, confirmation, identity, and audit tests |
| Error handling | deliberate dependency/capability failures and useful recovery |
| Deployment | recorded service/health checks and version/configuration used |
| Performance | latency/timing measurements under named hardware/model configuration |

## Usability evaluation

A small consented user evaluation can provide evidence for the functional client. Do not treat this as a learning-effectiveness study.

For the capstone stakeholder session, the FarmPi Stakeholder Presentation Pack is the **minimum standard onboarding** and is shown **before** the practical phone test. This reflects the intended real deployment model: a customer would receive at least a short product introduction during sale/installation rather than being handed an unexplained system.

The practical evaluation therefore tests three separate questions:

1. **Onboarding sufficiency** — is the short presentation enough to prepare the participant, or would deployment require more training such as a video, guided walkthrough, quick-start sheet, or hands-on instruction?
2. **Knowledge transfer** — can the participant carry the concepts from the presentation into the live application even where the presentation images are not identical to the current phone interface?
3. **Post-onboarding usability** — after the minimum orientation, can the participant complete realistic FarmPi tasks without further coaching?

Once the practical test begins, do not provide additional coaching unless the participant becomes genuinely stuck. If assistance is required, provide it and record exactly what help was needed. This session does **not** claim to measure zero-context discoverability.

Useful tasks include whether a user can:

- connect to and recognise the application state;
- ask for a current value in their own words;
- understand when a requested add-on measurement is not installed/reported for that paddock;
- request and interpret a historical graph;
- distinguish a farm-wide graph from a named-paddock or comparison view;
- recover after a speech or paddock-name misunderstanding;
- understand when FarmPi lacks the requested data;
- locate evidence/source information when needed;
- use voice/TTS and stop playback;
- change presentation settings without losing the main task.

Record task completion, hesitation/confusion, failure points, participant comments with consent, and resulting design actions. Do not claim production usability, accessibility compliance, agronomic effectiveness, or safety certification without suitable evidence.

## Performance evaluation

Record end-to-end latency and the existing response timing stages under a named hardware/model/configuration. Compare deterministic direct answers separately from model-assisted interpretation/explanations.

Model size, tokens per second, memory use, reasoning configuration, and context size are implementation evidence for the AI/data subsystem. They should be assessed against application responsiveness and deployment feasibility.

Historical model measurements belong in [Local LLM evaluation history](history/local-llm-evaluation.md). For the current proof-of-concept deployment, record the Pi-local Qwen3 0.6B Q4_K_M configuration and end-to-end latency with the development PC removed from the inference path. Compare those results with the retained historical 1.7B/reference-model measurements rather than assuming the smaller model is acceptable.

## Historical learning/course checks

The current repository still contains the earlier Learn/course feature. While it remains in the build, regression testing should ensure it does not crash or corrupt normal application state. It is no longer necessary to expand course-specific acceptance evidence unless the feature is retained as a current product requirement.

The original course rationale is preserved in [course-design.md](course-design.md).

## Documentation release check

Before publishing a material change:

1. update the owning guide and affected Mermaid source;
2. remove, archive, or clearly label superseded current-state text;
3. check local Markdown links and documented paths;
4. compare commands, environment names, endpoints, and defaults with code/configuration;
5. run automated checks and record any limitation honestly;
6. apply the [current capstone outcome gate](capstone-governance.md).

## Reconciliation validation (27 September 2026)

- Untouched main: 147 Python tests, two failures reproduced (legacy simulated-provenance fallback and obsolete missing-sensor wording assertion).
- Replacement: 155 Python tests pass, including metadata-only mode preservation, missing LIVE capability rejection, mixed-sample provenance, current-mode reporting and console-helper behavior.
- Python compilation and console-helper help invocation pass. Bash syntax checks pass individually for setup, schema update, demo loader and the unchanged reset helper. Git whitespace validation passes.
- Android and ESP32 builds were not run: an Android SDK and Arduino CLI were not available in this workspace. MariaDB DDL/demo-loader execution and two-board hardware validation remain outstanding. The SQLite integration adapter does not validate MariaDB syntax.
- No merge, deployment, database reset or hardware flash was performed. Review as a draft until those environment-specific checks are complete.


## Qwen3 0.6B acceptance pass

The smaller Pi-local model is accepted only if it improves responsiveness without breaking the language layer that remains necessary. Deterministic farm operations are not model benchmarks because they should bypass generation entirely.

Record `timings.interpretation_ms`, `timings.llm_ms`, total response time, route intent and whether the result was correct for at least these classes:

- configured-location wording such as `What stats are available for Fred's paddock?` — expected deterministic result and zero LLM generation time;
- a natural paraphrase that needs semantic interpretation but maps to an existing FarmPi operation;
- a short explanation such as `What does soil moisture percentage mean?`;
- a contextual follow-up such as `Can you explain that more simply?`;
- an unavailable measurement such as `What is the nitrogen level in Fred's paddock?` — no invented reading;
- a forecast/decision boundary such as `What will Fred's soil moisture be tomorrow?` or `Should I irrigate Fred's paddock now?` — no unsupported farm-specific prediction or instruction.

If the 0.6B model becomes unreliable on these linguistic cases, the result is evidence for choosing a larger model; do not move deterministic calculations back into the model to compensate.


## Graph screenshot acceptance

For at least one historical time-series chart and one two-location comparison chart, capture the installed Android client and verify:

- the plot background matches the FarmPi light theme and does not inherit an unrelated Material/purple tint;
- the chart title identifies the measurement;
- the Y axis is labelled and includes numeric scale values;
- the X axis is labelled as Local time, Location, or Observation as appropriate;
- representative X labels are visible and correspond to the actual returned labels;
- Low / Latest / High values match the plotted dataset;
- changing Line / Area / Bars / Dots does not change the underlying values;
- simulated data remains identified elsewhere in the response/status rather than being visually mistaken for physical sensor acceptance.

Screenshots are presentation evidence only. They do not replace deterministic graph-payload tests or physical-sensor acceptance.


## Managed simulation shape acceptance

The managed ESP32-S3 SIMULATED mode is test telemetry, but it should still produce plots that exercise the application realistically rather than manufacturing rapid oscillations that dominate screenshots.

With the current managed firmware and the relevant channels configured **SIMULATED**, verify over sufficient time that:

- soil moisture does not complete repeated high/low cycles within an hour; absent synthetic rain it should change slowly across a day;
- a synthetic rain event produces a gradual moisture rise rather than an instantaneous full-event jump;
- light is zero at night and follows one smooth daylight arc between date-dependent Hamilton sunrise and sunset;
- air temperature shows one daily heating/cooling cycle and soil temperature changes more slowly;
- relative humidity broadly opposes daytime heating rather than following the same waveform;
- barometric pressure and wind do not repeat on a one-hour cycle;
- pH and EC are near-stable over short periods;
- the two managed nodes are similar but not identical because node-specific offsets are applied.

These checks validate simulation usefulness only. They do not establish local weather accuracy or physical-sensor performance.

## Physical soil-moisture acceptance — 2 October 2026

The first physical channel has now been accepted end to end on FP-001 / HW 33C0 using the XC4604 analogue probe on GPIO4. Retained evidence is in [XC4604 LIVE soil-moisture acceptance](evidence/s3/soil-moisture-live-acceptance-2026-10-02.md).

Acceptance demonstrated:

- Android selected `soil_moisture_pct = LIVE` and the node returned to IN SYNC;
- dry and wet conditions produced materially different physical ADC-derived values;
- serial and MariaDB agreed for sample sequence 6860 at 64.69%;
- MariaDB stored per-measurement provenance as `LIVE`;
- Android displayed the corresponding current/history change.

This passes the soil-moisture component only. T01 remains **PARTIAL (1/6 physical measurements demonstrated)**. The original 2 October acceptance used an uncalibrated electrical display scale. On 3 October the first coco-relative calibration used provisional endpoints of raw 1066 dry / raw 1955 wet from the retained observations. Further saturated-coco testing then led to the retained firmware engineering endpoints of raw 1000 = 0% and raw 2200 = 100%. The resulting value is a **relative coco-moisture prototype scale**, not volumetric water content or agronomic accuracy evidence. Older screenshots captured under the provisional scale remain valid end-to-end path/provenance evidence but are not evidence of the final 1000/2200 percentage scale. See [XC4604 coco-relative calibration](evidence/s3/soil-moisture-coco-calibration-2026-10-03.md).

## Measurement drill-down acceptance

On the installed Android client:

- Dashboard has no duplicated soil-moisture sparkline/full trend block;
- tapping a graphable farm-summary measurement opens its farm-wide History graph;
- opening a configured location such as Fred's paddock and tapping soil moisture, temperature, humidity, light or pressure opens that location's graph directly;
- optional graphable measurements such as pH, EC, rainfall, wind speed, pasture height and leaf wetness can also be opened when present;
- wind direction does not advertise a misleading ordinary trend graph;
- 6 hours, 1 day and 7 days are selectable;
- the opened History screen preserves the selected location/measurement and still uses deterministic graph data rather than the LLM.


## Android graph timezone acceptance

FarmPi database/API timestamps remain UTC. The Android graph presentation must use the phone's system timezone without requiring a FarmPi timezone preference.

Automated JVM coverage verifies that `2026-09-28T05:35:00Z` formats as `28 Sep 18:35` for `Pacific/Auckland` during NZDT, while the same instant remains `05:35` in UTC.

On the installed Android client, verify a graph generated from a known recent UTC database row:

- the X-axis caption reads **Local time**;
- timestamp tick labels show the actual local date/time, for example `28 Sep 18:35`;
- the displayed time agrees with the phone clock/timezone;
- changing the phone timezone and reopening/re-rendering the graph changes only the displayed labels, not the data values or point spacing;
- no user-configurable FarmPi timezone setting is required.
## Time-system acceptance

FarmPi stores operational timestamps in UTC and presents local time only at the client/display boundary. Time validation must therefore check both the host time authority and the end-to-end node/database path.

### FarmPi host clock

Run on the Raspberry Pi:

```bash
date
date -u
timedatectl
```

Acceptance criteria:

- local time reports the intended deployment timezone `Pacific/Auckland`;
- the local abbreviation/offset matches the current NZ daylight-saving state;
- UTC differs from local time by the correct offset for that date;
- `System clock synchronized: yes`;
- NTP is active;
- the Pi is not relying on a local-time RTC setting.

Recorded live result on **28 September 2026 at 18:31 NZDT**:

```text
Mon 28 Sep 18:31:24 NZDT 2026
Mon 28 Sep 05:31:24 UTC 2026

Local time: Mon 2026-09-28 18:31:24 NZDT
Universal time: Mon 2026-09-28 05:31:24 UTC
RTC time: n/a
Time zone: Pacific/Auckland (NZDT, +1300)
System clock synchronized: yes
NTP service: active
RTC in local TZ: no
```

Result: **PASS for the FarmPi host clock/timezone/NTP layer.** The local and UTC times differ by 13 hours, matching NZDT on the test date.

### Managed-node and database timestamp path

The host-clock result does not by itself prove the ESP32 observation clock or database ingest timestamps. For end-to-end verification, inspect recent managed-node readings and compare `observed_at` with `received_at`:

```sql
SELECT
    s.node_uid,
    p.name AS location,
    r.sample_seq,
    r.observed_at,
    r.received_at,
    TIMESTAMPDIFF(SECOND, r.observed_at, r.received_at) AS observed_to_received_seconds,
    r.clock_offset_seconds,
    r.clock_out_of_tolerance
FROM readings AS r
JOIN sensor_nodes AS s ON s.id = r.sensor_node_id
JOIN paddocks AS p ON p.id = r.paddock_id
WHERE s.hardware_uid IS NOT NULL
ORDER BY r.received_at DESC
LIMIT 20;
```

Expected result:

- `observed_at` and `received_at` remain UTC database values;
- recent samples from both managed nodes are only seconds apart;
- `clock_offset_seconds` is close to zero;
- `clock_out_of_tolerance` is false;
- no one-hour offset appears across the daylight-saving transition.

Recorded live managed-node result on 28 September 2026:

- FP-003 / Fred's Paddock: recent samples showed `observed_at` to `received_at` delays of about 1.9-2.0 seconds;
- FP-001 / Bobs Paddock: recent samples showed delays of about 2.6 seconds;
- `clock_out_of_tolerance` was `0` for all 20 inspected rows;
- sample sequences were monotonically increasing;
- both nodes were continuing to submit fresh telemetry;
- no one-hour offset appeared after the NZ daylight-saving transition.

Result: **PASS for the managed-node -> FarmPi -> MariaDB timestamp path.**

Client acceptance must separately verify that UTC API timestamps are rendered in device-local time for the farmer.


## Visible graph time-tick acceptance

On an installed Android client, open at least one Light graph and one Soil Moisture historical graph.

Acceptance requires:

- a visible **Start / Middle / End** row beneath the plot;
- each position shows an actual local date and clock value, not only an axis caption;
- the X-axis caption reads **Local time**;
- the displayed times agree with the phone timezone;
- graph values and point spacing are unchanged.

A graph that only says `Time` or `Local time` without visible timestamp values does **not** pass this acceptance check.
