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

- measurement validation and natural-language aliases;
- telemetry time, sequence, deduplication, and ingest behaviour;
- database operations and paddock identity;
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

Farm facts must be testable without an LLM. Current readings, history, comparisons, device state, timestamps, calculations, and chart values must assert exact deterministic results and must not substitute generated text for database evidence.

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
6. switching through every offered visual mode and confirming that values do not change.

A generic graph request must not invent a paddock name from phrases such as `the soil moisture over 24 hours` or `the lighting of the paddock`. The application should use farm-wide data when that is the appropriate supported meaning.

## Functional query acceptance

The following groups should be exercised as an end-to-end user journey:

- **Conversation continuity:** ask a question, then use pronouns or shorthand such as `explain that more simply` and `why does that matter?`.
- **Open information:** ask a farm question, an adjacent technical/agricultural question, and an unrelated safe informational question.
- **Provenance:** compare deterministic FarmPi data, reviewed source material, and model/general knowledge.
- **Deterministic consistency:** ask for the same farm value using several phrasings and confirm the number is identical.
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

Also submit one authenticated ingest sample, retry the same sensor/sequence to confirm deduplication, ask for its exact value, request a historical calculation and graph, test a broader general question, and verify that a stopped database or LLM is described honestly.

Do not record credentials in test output or evidence documents.

## Requirements traceability

Every material change should link implementation, verification, and capstone evidence:

| Concern | Required evidence |
|---|---|
| Functional requirement | working end-to-end behaviour plus acceptance result |
| Architecture | component/responsibility mapping and rationale |
| Farm facts and calculations | exact fixtures, provenance fields, failure-path tests |
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

Historical model measurements belong in [Local LLM evaluation history](history/local-llm-evaluation.md).

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
