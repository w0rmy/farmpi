# Testing, evaluation, and capstone evidence

FarmPi now needs evidence that the integrated application works as designed and that the implementation demonstrates the current electives: **Advanced Application Development Concepts** and **Artificial Intelligence and Data Science**.

The evaluation focus is therefore functional, architectural, integration-based, and evidence-led. Earlier learner/course evaluation remains historical work rather than the current primary acceptance target.

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

Historical model measurements belong in [Local LLM evaluation history](history/local-llm-evaluation.md). For the current proof-of-concept deployment, also record the Pi-local Qwen3 1.7B configuration and end-to-end latency with the development PC removed from the inference path.

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
