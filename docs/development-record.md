# FarmPi development record

This record captures material design decisions and their outcome/evidence rationale. Current operating instructions live in the subject guides; historical performance measurements live under `docs/history`.

## 26 September 2026 - live Raspberry Pi backend validation

After the managed ESP32-S3 deployment/documentation update, the FarmPi validation suite was run on the deployed Raspberry Pi from `~/farmpi` using the Pi's Python 3.13 virtual environment.

Result:

```text
Ran 146 tests in 1.291s

OK
```

All 146 backend tests passed. The run included the managed-node test suite and exercised the semantic-interpreter failure path; the diagnostic `FarmPi semantic interpretation failed; using fast-route fallback: Semantic interpreter did not return a JSON object.` was emitted while the suite still completed successfully, consistent with the intended fallback behaviour.

Two non-failing deprecation warnings were observed:

- `sqlite3` warned that Python's default datetime adapter is deprecated as of Python 3.12. The warning is triggered by the SQLite test adapter in `tests/test_node_management.py`, not the MariaDB production data path.
- FastAPI/Starlette warned that `HTTP_422_UNPROCESSABLE_ENTITY` is deprecated in favour of `HTTP_422_UNPROCESSABLE_CONTENT`. The repository still uses the older constant in `app/ingest_api.py`.

These warnings do not invalidate the test result, but they are maintenance items worth correcting so future Python/FastAPI upgrades do not turn them into failures. This run is stronger deployment evidence than the earlier Windows/test-environment validation because it was executed directly on the live FarmPi Raspberry Pi.

## 26 September 2026 - live S3 deployment, fault isolation and local-model confirmation

### Physical node bring-up

After the managed-node implementation was merged into `main`, two ESP32-S3 N16R8 boards were flashed and exercised against the live FarmPi deployment. Both joined the dedicated FarmLAN and reached the managed discovery/registration flow. The Android Nodes interface was used to connect/register the boards with FarmPi, moving this work beyond compile/test-adapter evidence into live hardware/application integration.

Observed hardware UIDs were `7c4fadb633c0` and `7c4fadb52c40`. Hardware UID remains an identifier rather than an authentication secret. Final assigned FarmPi node IDs, desired/applied full configuration fingerprints and screenshots still need to be captured as formal evidence; no real sensor observation is claimed by this entry.

Two bring-up faults were diagnosed without changing application/network logic unnecessarily:

- One board reported `phy_init: store_cal_data_to_nvs_handle: store calibration data failed(0x1105)` after flashing. A deliberate full-flash erase followed by reflashing cleared the condition and the firmware then reached `Awaiting registration`. Normal updates should continue to preserve NVS; erase-all is a provisioning/recovery action.
- Another board entered a reboot loop with the lwIP assertion `sys_untimeout ... Required to lock TCPIP core functionality!`. Although the symptom appeared to implicate the TCP/IP stack, the fault was traced to an unintended breadboard connection. Removing that connection restored normal operation. This is retained as evidence of cross-layer fault isolation rather than rewriting the incident as a software defect.

### FarmLAN and endpoint scope

The live prototype uses a dedicated FarmLAN wireless access point on the Raspberry Pi while retaining a separate management/home-LAN connection. The FarmLAN connection profile is bound to the intended Wi-Fi radio by MAC address rather than relying on a persistent `wlanN` name. The AP-side address is `10.42.0.1/24`, while application clients continue to use `https://farmpi.local/` because the current Caddy certificate is issued for that DNS name.

A possible future hardening step is to make physical nodes use the fixed AP-side IP directly and issue a certificate containing that IP as a Subject Alternative Name. This was deliberately deferred because the existing `farmpi.local` path is adequate for the proof of concept and changing PKI/addressing now would add complexity without improving current capstone evidence.

### Pi-local LLM confirmation

The Raspberry Pi deployment was inspected directly. `farmpi-llm.service` was active and running `llama-server` on `127.0.0.1:8080` with `lmstudio-community/Qwen3-1.7B-GGUF:Q4_K_M`, context 2048, reasoning disabled and one parallel slot. `/health` returned `{"status":"ok"}` and `/v1/models` reported the same Qwen3 1.7B model.

`farmpi.service` loads `/etc/farmpi/farmpi.env`. That environment currently contains no `FARMPI_LLAMA_URL` override, while `app/app.py` defaults `FARMPI_LLAMA_URL` to `http://127.0.0.1:8080`. The normal inference path is therefore FarmPi backend -> Pi-local llama.cpp -> Qwen3 1.7B; the development PC is not required.

A faster model on the development PC remains technically possible, but Jeremy chose the Pi-local model for proof-of-concept testing because it removes a separate machine and changing LAN address from the deployment, preserves the intended offline/local architecture, and makes the test boundary more reproducible. Slower inference is accepted as an explicit prototype trade-off and should be measured rather than hidden.

### Android scope decision

The client direction was reviewed after the elective change. Jeremy chose to reshape the existing Android client rather than rewrite it. Working application capabilities - Ask, voice/TTS, graphs, provenance, settings, connection state and Nodes administration - are retained. Course/module/progress surfaces created for the superseded Developing Flexible IT Courses elective are now candidates for removal. Contextual explanation and measurement interpretation remain because they are FarmPi/AI functionality, not evidence of a course by themselves.

This is another scope-control decision: preserve working architecture that still supports the current requirements, remove obsolete elective-specific product behaviour, and avoid a rewrite that would add integration risk without demonstrating new capstone value.

## 26 September 2026 - two physical S3 nodes and centrally managed configuration

### Inspection and decisions

Started from local FarmPi revision `da6a109671ff9f5ce43dc3339ab256e0954d4e0d`. The original `F:/FarmPi` checkout contains staged Android icon changes, which remain untouched. Implementation is in an isolated checkout on `feature/s3-node-configuration`. Its exact final revision is the commit containing this entry; source and dependency evidence accompanies it under `docs/evidence/s3`.

Inspected the existing ESP32 sketch, measurement catalogue, ingestion models/storage, MariaDB schema, current/history queries, Android Compose activity and HTTPS helper before editing. Contrary to the older handover statement that all 13 values were required, this revision already made seven optional; six remained mandatory, and latest-reading SQL still filtered for all six. Both paths needed correction. Reused the existing catalogue, sensor_nodes/readings tables and API rather than creating a second telemetry system.

Jeremy corrected an initial AI proposal to hard-code a six-sensor physical payload and required per-node configuration across the existing 13-measurement catalogue. The six remain the FR01 final physical acceptance minimum, not a fixed per-node payload. Jeremy also challenged increasing human-facing configuration numbers for long-term supportability. The agreed correction is a full SHA-256 fingerprint of canonical current state, short UI support code, independent numeric schema version and latest-complete-state pull/apply/ack. These are material human corrections to scope and technical reasoning.

Jeremy identified his boards during this task as ESP32-S3 N16R8. The compile target uses 16 MB flash and octal PSRAM; exact carrier pin layout and probe/module are not yet identified. The bring-up board profile therefore touches no GPIO and advertises soil-moisture configuration support without pretending to implement acquisition. It can show configured but not reporting, never a fabricated physical measurement.

### Implemented behaviour

Pending discovery and explicit administrative registration extend sensor_nodes. Registration starts empty, hardware UID is separate from assigned node UID and location, and device-generated NVS credentials prevent UID-only impersonation. The Android Nodes screen lists identity, location, firmware, last contact, desired/applied support codes, derived sync state, all catalogue choices and sensor runtime states. Unsupported capabilities cannot be enabled. Administrator credentials are session-only in the UI.

Firmware validates complete canonical state, schema, identity, capabilities and SHA-256; it uses two NVS slots with read-back before switching. Existing simulator firmware is preserved and explicitly simulated. Physical ingestion validates registered device credentials, applied and desired enablement, capability, values, timestamp, sequence and provenance. Sparse values are accepted without inventing absent observations. Actual location is captured on each reading; relocation preserves stored history and rejects late samples with an old assignment epoch. Old pre-migration location movements cannot be reconstructed from data that was never recorded.

Current-reading queries no longer require six values, moisture-specific paths filter absent moisture, and valid delayed observations retain their original time in history. Charts label simulated content. Configuration support, actual acquisition, desired enablement and reporting status remain separate. The current S3 target emits no telemetry until the real probe driver is implemented.

### Verification and failures

* Baseline: 135 Python tests passed.
* First changed-suite run: four failures and one error exposed tests tied to the old mandatory baseline/null/column-position contract. Updated the expectations for intentional contract changes; retained the failure output as evidence.
* Updated backend: 146 tests passed, including transactional API flows using a SQLite test adapter, two-node isolation, empty registration, credential failures, sparse physical samples, exact retries, changed-content retry rejection, disabled/unsupported sensors, provenance rejection, stale acknowledgements, failed update retaining applied state, relocation, and contact recovery. This is not evidence that the MariaDB DDL was executed.
* A later regression check flagged the newly added spoken provenance sentence against an older exact-answer expectation. Updated that test to require the simulated-data disclosure and retained the failure output. Added actual sparse current-query and relocated named-history checks using the test adapter.
* Python compileall and Git whitespace checks passed. Dependency versions are recorded.
* ESP32 build passed with Espressif Arduino core 3.3.11 and ArduinoJson 7.4.2, S3/16M/OPI PSRAM target. Final output: 1,006,226 bytes flash and 46,684 bytes global RAM. Compilation used placeholder network/certificate configuration; it is not a provisioned or flashed image.
* Android Gradle 9.3.1 build was attempted with the installed Android Studio JDK. It failed before Kotlin compilation with `Unable to establish loopback connection`. No Android build/device pass is claimed.

### Outstanding physical and deployment evidence

Run the migration twice against a disposable MariaDB copy before live deployment, compile and exercise Android on a working toolchain, provision CA/local NTP and both boards, then follow [the two-board checklist](s3-node-bringup.md). NVS reboot/power-loss behaviour has been implemented but not demonstrated on hardware. Device credential recovery after deliberate NVS erasure is a future administrative operation, not automatic reassignment. The next acquisition driver needs persistent sequence allocation and explicit offline-buffer semantics.

Neither the Pi nor either S3 was deployed/flashed in this task. No physical measurement was demonstrated. **T01 has not passed**: all six FR01 physical measurements and FR02 identity/provenance evidence remain required. The exact soil-moisture module, electrical interface, calibration and final shared pin profile must be established before sensor wiring/driver work.

## 15 September 2026 - live application behaviour realignment

Following the documentation pivot, the live prompts and recovery wording now describe a conversational farm-monitoring assistant. Informational requests no longer receive an automatic agricultural-learning framing. Reviewed measurement explanations, general information, source attribution rules, deterministic farm-data authority, and bounded conversation history remain available.

Android now separates the saved course return location from the context of an ordinary question. Only explicit course activities and course quick actions send a module ID. Course quick actions follow the successful course response, while the Learn tab, course payloads, saved progress, and existing preference keys remain intact. Historical course content and prior development records have not been rewritten.

This supports **Advanced Application Development Concepts** through client state separation, recovery, and compatibility, and **Artificial Intelligence and Data Science** through consistent prompt scope, governed interpretation, and verification that model failure cannot alter chart values.

Validation: the baseline backend suite passed 122 tests. The updated suite passes 125 tests, including new API-level checks for non-farm information without farm readings, explicit course context followed by ordinary conversation, and exact graph/evidence responses during model failure. Conversation tests now exercise the actual application and interpreter prompts. The Android compilation attempt could not start its Gradle process because the environment reported `Unable to establish loopback connection`; Android compilation/device acceptance and live Raspberry Pi/model checks remain unverified.

## 15 September 2026 - capstone direction realignment and documentation cleanup

### Direction change

On **2 September 2026**, the agreed capstone direction changed from **Developing Flexible IT Courses** to **Advanced Application Development Concepts**, while retaining **Artificial Intelligence and Data Science**. This is a genuine project pivot, not a correction to the historical record. The learning/course work below remains valid evidence of the development process and should not be rewritten as though the current direction existed from the beginning.

FarmPi is now treated as a **functional farm-monitoring application demonstrator**. The project remains a prototype/concept demonstrator rather than a production-ready farm product. The capstone evidence chain is now:

**need statement -> functional, architectural, and quality requirements -> hardware/software mapping -> architecture -> implementation/integration -> deployment -> testing/evaluation evidence**

The application itself is therefore central to the capstone evidence. Current priorities are coherent end-to-end behaviour, mobile usability, service/data integration, deterministic analytics and graphing, AI/data integration, failure recovery, deployment, testing, and technically defensible architecture.

### Reinterpretation of existing work

A substantial amount of the existing implementation remains valuable under the new electives:

- Android/Compose, voice/TTS, local state, chart rendering, settings, API consumption, and error states contribute to **Advanced Application Development Concepts**.
- FastAPI, Caddy, MariaDB, the ingest pipeline, paddock identity/audit logic, modular Python responsibilities, and Raspberry Pi deployment contribute to application architecture and integration evidence.
- Deterministic analytics, graph payloads, semantic interpretation, bounded conversation context, model compatibility work, source/provenance handling, and model evaluation contribute to **Artificial Intelligence and Data Science**.
- Integration faults already found - conversation follow-up failure, Qwen thinking/token behaviour, TTS `null` becoming a four-character spoken string, graph compilation/routing issues, and incorrect paddock extraction from generic graph language - are useful iterative development and debugging evidence.

The earlier Learn tab, five-module course, course progress, learner-adaptation rationale, and associated tests may remain functional, but they are now legacy features from the superseded elective direction rather than the primary reason for new development.

### Functional acceptance findings carried forward

A current manual acceptance pass found the conversation, open-information, provenance, and deterministic-consistency areas broadly working before graph testing exposed further integration issues.

Graph testing identified several application-level problems:

- `Can you show me the soil moisture over 24 hours?` could be misread as requiring a paddock and could treat phrases such as `the soil moisture over 24 hours` as a paddock candidate.
- generic light/day-profile wording could similarly drift into invalid paddock extraction;
- daylight requests could show a valid graph while also returning an internal message that a deterministic operation was unavailable;
- user-facing text such as `The requested deterministic operation is unavailable for this measurement` exposed internal implementation language;
- the language model could produce a generic `I cannot produce graphs` style answer even though graph capability belongs to the FarmPi application, not to the model itself.

These findings changed the desired recovery model. When a literal request cannot be completed directly, FarmPi should attempt semantic interpretation, inspect available measurements/operations/graphs, map defensible nearby concepts, offer a valid alternative, and ask for clarification only when genuinely necessary. A generic model refusal should not override application capabilities.

This recovery behaviour is now treated as **application usability and resilience**, not as a learning-platform requirement.

### Documentation and source realignment

The current repository documentation was rewritten to reflect the new direction while preserving historical evidence:

- the root README now presents FarmPi as a functional application demonstrator;
- `docs/capstone-governance.md` now maps scope to Advanced Application Development Concepts and Artificial Intelligence and Data Science;
- `docs/architecture.md` now describes the Android/FastAPI/MariaDB/analytics/LLM system as an integrated application architecture;
- `docs/android-client.md` now treats the phone client, graphing, voice/TTS, state, and error recovery as mobile-application evidence and marks the course UI as legacy;
- `docs/data-and-api.md` now describes the main application API, farm-wide/named/comparison graph semantics, and capability lookup;
- `docs/learning-and-sources.md` has been repurposed as the current AI/grounding/source-integration guide;
- `docs/testing-and-evaluation.md` now prioritises functional, integration, mobile, AI/data, failure-path, deployment, and performance evidence;
- the former flexible-course design remains explicitly marked historical rather than being deleted;
- Mermaid indexes and the semantic/grounding/Android flow diagrams were updated to use current user/application terminology;
- `app/main.py` and `app/semantic_interpreter.py` were cleaned up so current source comments/prompts refer to users and application behaviour rather than treating every interaction as a learner interaction.

A separate historical note at `docs/history/2026-09-02-elective-pivot.md` records the elective switch and rationale without rewriting the earlier entries below.

### Current scope rule

New work should now be challenged with:

> **Does this make the FarmPi application more functional, coherent, reliable, usable, testable, or technically defensible against the current capstone requirements?**

IoT expansion, production hardening, cloud services, additional radio work, or further course/LMS development remain out of scope unless a current requirement makes them necessary.

## 30 August 2026 - Module 1: Getting Started with FarmPi

### Learner need and design reasoning

The existing embedded course had a general first module, but it did not give a new learner a sufficiently concrete, client-first start before moving into farm information. The learner need is to become comfortable operating FarmPi itself: find Ask and Learn, understand the visible settings and status message, use ordinary language and voice, stop spoken output, seek guidance when unsure what to ask, and make the presentation comfortable. FarmPi is assumed to be already installed, statically configured, connected, and ready. Teaching addresses, certificates, Raspberry Pi setup, backend configuration, or connection administration would distract from that learner outcome and remains out of scope.

Module 1 is now **Getting Started with FarmPi**. Its canonical reviewed definition in `app/learning.py` supplies the Android Learn surface, so the learner-facing content does not have a hard-coded Android duplicate. The module follows the existing **Learn → Try → Ask → Check → Continue** sequence. Learn content is deliberately short and action-oriented: it introduces Ask, Learn, the settings cog, and the connection-status message; then typed and microphone questions, speech/Stop, Guide me, suggested/follow-up questions, Explanation depth, Guidance, themes, and Text size.

The Try activity makes the learner compare Simple and Technical responses while changing text size and theme, rather than merely reading that presentation is flexible. It states that settings change how learning is presented, not underlying facts or the required learning outcome. The Check is an ungraded practical self-check: it confirms the key controls and asks what to change when an explanation is too technical and what to use when the learner is unsure what to ask next. Continue uses the learner-facing transition to the existing Module 2, **Understanding the Application**. The backend payload now has reviewed `continue_content`, and the Android client renders that field for every module instead of using a generic continuation sentence.

### Outcome, scope, and reuse mapping

| Change | Outcome contribution | Scope control |
|---|---|---|
| Client-first Module 1, practical Try, self-check, and Module 2 continuation | Developing Flexible IT Courses: coherent onboarding, constructive alignment, learner agency, and authentic practice | No LMS, account, grade, gamification, or new course engine |
| Reused Ask, voice, spoken output/Stop, Guide me, suggestions, and Return to Module | Developing Flexible IT Courses: multiple learner interaction routes and supported exploration | No new AI agent, voice service, or second conversation path |
| Reused explanation/guidance, six themes, and text-size settings | Developing Flexible IT Courses: presentation/access flexibility and learner preference | Presentation only; does not alter facts, assessments, or learning outcome |
| Validated module context and reviewed canonical payload | AI and Data Sciences: constrained, inspectable use of the existing AI conversation boundary | No client-controlled prompt context, farm-data interpretation, IoT, cloud, or infrastructure work |

### Verification and limitations

- Added focused course-definition assertions for Module 1 title, LO1-only relationship, next-module link, valid real Try intent, learner controls, explicit non-administrative connection boundary, practical self-check prompts, and continuation text. Existing deterministic payload and reviewed-context tests continue to cover the canonical API contract.
- Python: `.venv\Scripts\python.exe -m unittest discover -s tests -p 'test_*.py' -v` passed **122 tests**; `.venv\Scripts\python.exe -m compileall -q app tests` and `git diff --check` passed. The run emitted the existing FastAPI/Starlette TestClient deprecation warning and one expected semantic-interpreter fallback log line; neither was a test failure.
- Android: with `JAVA_HOME` set to the installed Android Studio JBR, the documented `gradlew.bat :app:assembleDebug` build was attempted. The sandboxed attempt could not create its normal Gradle wrapper-cache lock. The approved normal-cache attempt reached Gradle but failed before Kotlin compilation with `Unable to establish loopback connection`, a managed-environment restriction. Android device acceptance still requires a trusted development certificate, available microphone/TTS services, and real portrait/landscape/small-screen observation; no learning-effectiveness or accessibility-compliance claim is inferred from implementation alone.

## 30 August 2026 - course documentation synchronization and Raspberry Pi validation evidence

### Documentation synchronization

After the embedded flexible IT course implementation was committed in `0011648`, the repository documentation was reviewed against the code and Android flow, then synchronized in `950f479`. The update made the course a first-class current feature rather than leaving it described only in its dedicated design document.

- The root README and documentation index now identify the five-module embedded course and local course return/progress as current FarmPi capabilities.
- The Android guide records the Ask/Course surfaces, **Learn → Try → Ask → Check → Continue** pattern, free navigation, recommended continuation, minimal device-local progress, Return to Module, contextual learning links, retained module context, and course-specific acceptance checks.
- The Data and API guide documents `GET /api/learning/course`, the compatible `/api/learning/activities` endpoint, the validated optional `course_module_id` on `/api/ask`, HTTP 422 behaviour for an unknown module id, server-only reviewed prompt context, and reviewed-course-module provenance.
- Architecture, learning/source, capstone-governance, testing/evaluation, and Mermaid diagram sources were updated so authority boundaries, scope control, evidence mapping, Android local state, and the one-conversation design agree with the implementation.
- Terminology now uses **Text size**, matching the actual Compose font-scale preference, rather than implying that the application changes Android display density.

This documentation work supports Developing Flexible IT Courses by making constructive alignment, learner pathway choice, local temporal flexibility, and accessibility/presentation choices inspectable. It supports AI and Data Sciences by documenting controlled model context, provenance, and the deterministic authority boundary. It introduces no new product scope.

### Raspberry Pi validation evidence

During the subsequent Pi update, the deployment script reported a successful Python validation run:

```text
Ran 121 tests in 0.357s

OK
```

The output also showed a `StarletteDeprecationWarning` concerning `fastapi.testclient`/`httpx` and a semantic-interpreter fallback log line. Neither caused a test failure. The update then proceeded to service installation and **Applying FarmPi database schema updates**.

At the time of this record, the supplied output does not confirm completion of the schema update, service restart, health checks, or Android device acceptance. Those steps must be recorded only after their actual output is available. The reported result is therefore evidence of the Python validation stage, not a claim that the entire deployment completed.

## 30 August 2026 - formal embedded flexible IT course

### Problem

FarmPi already supported natural-language Ask/Guide me, real teach-by-doing prompts, explanation and guidance adaptation, voice, themes, text sizing, charts, evidence/provenance, and bounded follow-up conversations. However, the Android Learn tab was a separate hard-coded flat prompt list while the backend exposed a different activity catalogue. The implementation demonstrated useful learning facilities but not a recognisable, coherent course with an aim, outcomes, sequence, return point, or authentic completion activity.

### Research-informed design decisions

- Replaced the flat catalogue as the primary learning model with one reviewed, version-controlled deterministic course definition in `app/learning.py`. It has an explicit aim, four learning outcomes, five modules, linked outcomes, controlled content, real Try instructions, success intents, quick prompts, lightweight checks, next-module references, and response-intent mappings. The older activities endpoint remains as a compatible projection rather than becoming a competing curriculum.
- Made the five modules visible as **Learn → Try → Ask → Check → Continue**: Getting Started; Understanding the Application; Using the AI Learning Assistant; Getting Help and Solving Problems; and Putting It Together. The final module is an authentic evidence-informed FarmPi enquiry, not a large multiple-choice quiz.
- Chose a recommended pathway without lock-in. Learners can open modules directly and return after exploration. Local preferences retain only the current/last module plus completed Try/check/module markers, deliberately avoiding accounts, cloud sync, grades, badges, profiles, or analytics.
- Reused real route intents as Try evidence. A matching genuine response can mark a Try complete, while Check is explicitly a learner reflection and not a claimed measure of competence.
- Kept the ordinary `/api/ask` conversation as the sole AI path. Quick actions request simpler/deeper/example explanations or one short learner-facing understanding question; they reuse the existing bounded conversation token and retain course context.
- Added bounded course-aware context. Android can supply only `course_module_id`; the API validates it against the canonical course and contributes only the matching reviewed context to model-assisted messages. It records reviewed-course-module provenance. Client text cannot inject course/system instructions, and deterministic farm authority, source hierarchy, and confirmation boundaries remain unchanged.
- Made Module 3 state the AI/data distinction directly: AI can explain and be challenged, but is not automatically correct; deterministic FarmPi observations/calculations and model knowledge differ; important information should be checked. Module 4 also explains clarification, provenance, and the absence of live web search.
- Reused the six existing themes, compact/standard/large text-size choices, voice, explanation depth, guidance frequency, and selectable charts. Settings wording now says Accessibility and learning settings / Text size. This provides adaptable presentation without claiming WCAG or other accessibility compliance.

### Outcome, scope, and evidence mapping

| Change | Outcome contribution | Scope control |
|---|---|---|
| Controlled aim/outcomes/modules and coherent learning pattern | Developing Flexible IT Courses: constructive alignment, guided and self-directed pathways, authentic activity | No LMS, gradebook, accounts, or content generator |
| Local progress and Return to Module | Developing Flexible IT Courses: temporal flexibility and learner agency | Device-local minimal state only; no cloud or learner analytics |
| Contextual AI quick actions and reviewed module context | Developing Flexible IT Courses: iterative explanation and help; AI and Data Sciences: constrained, inspectable model context | One existing conversation/API; no AI agent or arbitrary client prompt authority |
| Evidence/chart/source-aware modules and AI limitations | AI and Data Sciences: provenance, deterministic authority, critical model use | No farm decision, new control function, or live web-search claim |
| Theme/text/voice/chart reuse across course UI | Developing Flexible IT Courses: presentation/access flexibility | No custom artwork, animation, or broad Android redesign |

This passes the capstone outcome gate because each change directly supports Developing Flexible IT Courses and/or AI and Data Sciences. It does not add farm-monitoring, IoT, sensor, LoRa, cloud, control, or unrelated platform scope.

### Verification and limitations

- Added course-contract tests for unique module/outcome IDs, linked outcomes, next-module references, accepted success/context intents, deterministic course payload, invalid module handling, reviewed context isolation, and provenance.
- Python: `.venv\Scripts\python.exe -m compileall -q app tests` completed successfully; `.venv\Scripts\python.exe -m unittest discover -s tests -p 'test_*.py' -v` passed **121 tests**; `git diff --check` passed.
- Android: the documented JDK 17/Gradle debug build was attempted. The first sandboxed attempt could not create the normal Gradle wrapper-cache lock; the approved normal-cache attempt reached Gradle but failed before Kotlin compilation with `Unable to establish loopback connection`, a managed-environment restriction. Device acceptance remains necessary for certificate trust, voice services, physical screen sizes, and observed learner use; documentation now lists the course-specific checks. No learner effectiveness, accessibility conformance, or agronomic claim is inferred from implementation or automated tests.

## 29 August 2026 - interactive visual analytics expansion

### Context

The first Android chart renderer proved that deterministic database results could be visualised, but its presentation was deliberately minimal: comparisons were rendered as progress bars and time-series data as a small strip of vertical blocks. That was adequate plumbing evidence but weak as a learning interface because it made trends, daily shapes, and comparisons harder to perceive than necessary.

### Decisions

- Kept chart values entirely deterministic: the database/analytics layer remains responsible for selecting and calculating the values. The language model does not create, alter, smooth, or estimate graph data.
- Added a dedicated Android visualisation component that renders the existing verified chart payload at a substantially larger size with grid lines, clearer summary values, and theme-aware presentation.
- Added learner-selectable graph views. Time-series data can be switched between line, area, bars, and dots; comparison datasets can switch between bars and dots. Changing view type changes presentation only, never the underlying values.
- Light/lux time-series data defaults to an area-style **Day profile** view because the daily rise/fall pattern is visually meaningful and easier to interpret that way. The learner can still switch to the other supported views.
- Added low/latest/high summaries and simplified time labels so a learner can combine an immediate numeric cue with the graphical pattern.
- Kept the graph controls inside the result card rather than adding a separate graph-configuration workflow. This deliberately limits UI scope while still giving learners control over how information is represented.
- Added a defensive Android JSON check so a JSON `null` `spoken_answer` cannot become the literal four-character string `"null"`; the visible answer is used for speech instead.

### Outcome and scope mapping

| Change | Evidence contribution | Scope control |
|---|---|---|
| Selectable line/area/bar/dot presentation | Developing Flexible IT Courses: the same learning data can be represented in different visual forms to support learner preference and comprehension | Presentation changes only; no graph-design workstream or model-generated graphics |
| Larger trend/day-profile visualisation | AI and Data Sciences: database observations and deterministic analytics are made interpretable as visual data | No new IoT requirement and no change to factual authority |
| Low/latest/high visual cues | Developing Flexible IT Courses: supports quick interpretation before deeper inspection | Values come from the same chart dataset; no inferred farm conclusion |
| Theme-aware graph rendering | Developing Flexible IT Courses: existing visual-flexibility choices apply to data visualisation as well as text | Reuses existing themes rather than adding bespoke artwork |

This work remains in capstone scope because it directly improves how learners inspect and interpret data. It is not being justified as Android polish: the evidence target is flexible visual presentation and data interpretation. Further chart work should be rejected if it becomes cosmetic rather than improving those outcomes.

### Verification

The changes were pushed directly to `main`. This repository currently has no GitHub Actions build/check associated with the commit, so the Android changes still require a normal Android Studio/Gradle compile and device acceptance check. Manual acceptance should include a 24-hour light graph, a soil-moisture trend, and a multi-paddock comparison, switching through every offered view and confirming that displayed values do not change between views.

## 29 August 2026 - learning focus, evidence hierarchy, Android flexibility, and documentation baseline

### Context

The repository contained useful implementation records but too many overlapping “current” documents. Several described earlier Qwen3 0.6B/1.7B experiments beside the later Qwen3.5 reference setup without consistently distinguishing deployment, development, and history. The Android main screen also carried secondary learning preferences, and the grounding policy could be read as permission to reject low-relevance questions rather than as an evidence-quality rule.

### Decisions

- Made the capstone outcome focus explicit and immutable: the farm-monitoring system is the vehicle; the embedded learning platform is the capstone.
- Added an outcome gate for every feature, architecture choice, experiment, and evaluation. Work with no outcome contribution is rejected unless it is essential minimum infrastructure; negative effects on accessibility, agency, provenance, or teach-by-doing use must be flagged.
- Kept readings, historical values, timestamps, comparisons, calculations, device state, paddock identity, and mutations deterministic and authoritative. They are never invented by a model.
- Made relevance control evidence quality and depth, not permission to answer. General and apparently unrelated questions receive a concise useful answer with suitable uncertainty when safe.
- Established five evidence tiers: first-class trusted; trusted primary; reputable general; general/unverified web; model knowledge. First-class is a preference rather than blanket infallibility, except where a source is inherently authoritative for its own current content.
- Preferred DairyNZ and relevant New Zealand government sources for New Zealand dairy/agricultural topics. Curated metadata is not represented as live retrieval, and a reference-only source is visible as such.
- Added a top-right settings control, moved explanation/guidance preferences off the Ask screen, and added six lightweight whole-app themes plus compact/standard/large text density.
- Preserved model measurements as history and documented the checked-in Pi Qwen3 1.7B service separately from the Qwen3.5-9B development/reference setup.
- Consolidated current documentation into one owner per subject and deleted the superseded current-state, database, ingest, grounding, learning, simulator, analytics, paddock-admin, latency, and LLM-test documents.

### Outcome and scope mapping

| Change | Evidence contribution | Scope control |
|---|---|---|
| Natural-language useful-answer routing | Developing Flexible IT Courses: normal use becomes the learning interaction | Does not grant model authority over farm facts/actions |
| Five-tier evidence and provenance | AI and Data Sciences: source selection, governed model context, transparency | No claim of live research; no fabricated citation |
| Deterministic analytics and action confirmation | AI and Data Sciences: controlled data pipeline and explainable hybrid architecture | No model SQL, arithmetic, identity resolution, or mutation authority |
| Themes, text density, settings cog | Developing Flexible IT Courses: readability, contrast preference, cognitive comfort, learner adaptation | Six reusable presets; no custom graphics or animation workstream |
| Synthetic ESP32 telemetry | Repeatable data/evaluation context | Explicitly simulated; no agronomic validity claim; no expansion into LoRa/production IoT without outcome evidence |
| Model topology documentation | Transparent implementation/evaluation constraint | Model size and hardware are not treated as the capstone thesis |

### Verification

- Python: `108` unit tests passed.
- Python: `app` and `tests` compiled successfully with `compileall`.
- Documentation: all local Markdown links resolved and `git diff --check` passed.
- Android: the pinned Gradle 9.3.1 wrapper downloaded, but this managed Windows environment prevented Gradle from establishing its required local loopback connection before Kotlin compilation. The build must be repeated in Android Studio or a normal local shell; this is recorded as an environment limitation, not a passing app build.

### Follow-up evidence

Run the manual Android acceptance checks and the consented learner evaluation in [Testing and evaluation](testing-and-evaluation.md). Record observations rather than assumed learning or accessibility results. Any future LoRa, physical sensor, remote-control, cloud, model-size, or production-hardening proposal must pass the [capstone outcome gate](capstone-governance.md) before implementation.

## 29 August 2026 - LM Studio readiness compatibility

The development/reference model was verified as Qwen3.5-9B Q4_K_M in LM Studio, advertised to OpenAI-compatible clients as `qwen/qwen3.5-9b`. FarmPi had been checking the model server with `GET /health`; LM Studio returned success for that unknown route but recorded an error for every probe. FarmPi now uses the supported `GET /v1/models` endpoint, with regression coverage, and strips a trailing slash from `FARMPI_LLAMA_URL` before constructing endpoint paths.

This is a compatibility correction to the model integration boundary. It improves operational clarity without changing grounding, routing, source authority, learning behaviour, or the capstone focus. The PC-hosted model remains an implementation and evaluation choice rather than the capstone thesis, and its LAN endpoint must remain restricted to the trusted local network.

## 26 September 2026 — Android course UI retirement

Reshaped the existing Android client into Ask and Nodes destinations. Removed course navigation, module/progress state and course request context while retaining monitoring, contextual explanations, speech/TTS, graphs, provenance and settings. Historical course records and backend contracts are preserved. See [audit and validation record](android-ui-refactor-2026-09-26.md) for dependency analysis, the refactor boundary, 146 passing backend tests and the unresolved local Gradle loopback failure that prevented Android build/test/lint validation.


## 27 September 2026 — transition from synthetic farm state to managed-node operational baseline

### Transition issue identified

The earlier prototype used a centrally generated 16-location synthetic dataset as normal working data. That was useful while developing dashboards, graphing, conversational queries and deterministic analytics. Once two real ESP32-S3 managed nodes existed, the same arrangement became misleading: the application could still appear to have sixteen actively reporting locations while the real hardware had no physical probes.

Jeremy identified this as a design-transition problem rather than a reason to preserve the old prototype state. The synthetic readings have no operational value that justifies carrying their assumptions into the managed-node architecture.

### Decision

- Keep the old 16-location ESP32 simulator as an explicit test/demo tool, not the normal operational database baseline.
- Add an explicit destructive transition helper that archives the existing MariaDB database before recreating a clean operational database. Applying code alone never performs the reset.
- Separate immutable hardware UID, stable FarmPi logical node ID, friendly node name and farmer-defined location. Farmer locations may use ordinary names such as `Bob's` or `Down by the Trough`; moving hardware does not rename the hardware.
- Replace the earlier enabled/disabled sensor configuration with one explicit state per supported measurement: `OFF`, `SIMULATED`, or `LIVE`.
- Move simulation to the ESP32 sensor-driver boundary. A simulated reading must travel through the same device authentication, configuration fingerprint, clock/sequence, ingest, database and application path that a later physical reading will use.
- Preserve provenance per measurement in storage. A mixed development sample can therefore distinguish which values are simulated and which came from a live driver.
- Keep LIVE honest: selecting LIVE does not fabricate a value. Until the corresponding physical driver and probe exist, that measurement reports nothing.

### AI collaboration and judgement

The initial AI suggestion was to audit and separate the old synthetic database from the new physical-node state while preserving the existing dataset. Jeremy challenged that approach. Because the old observations were entirely synthetic, he proposed taking the opportunity to establish a clean operational baseline instead. He also proposed OFF/SIMULATED/LIVE as a per-sensor state so that each physical channel can move from simulation to a real probe without rebuilding the telemetry path.

Jeremy then identified a second usability/identity issue: farmers will normally use their own location names rather than generic labels such as Paddock A or Paddock B. This led to the explicit separation of hardware identity, FarmPi node identity and editable farmer location.

The resulting design is simpler than preserving two competing operational models and gives stronger provenance. It also records a practical consequence of evolving an existing prototype: earlier test assumptions can become architectural liabilities when the intent of the system changes.

### Evidence boundary

This work does not complete T01 or T02. Node-local simulated telemetry demonstrates the managed end-to-end software path only. T01 still requires the six FR01 measurements from real physical sensors. Persistent sequence allocation is present, but communication-loss buffering/recovery remains separate T02 work.


## 27 September 2026 — reconcile duplicate transition implementations

Two independent implementations of the same requested transition were opened as PR #10 and PR #11. Jeremy merged #10; #11 then conflicted. The duplicate work and delayed completion reporting caused avoidable confusion. The merge was preserved as the baseline, and remaining changes were rebuilt on top rather than applying the second implementation wholesale.

Jeremy's console-only source-mode boundary is restored: Android shows modes but does not submit changes to them. The replacement retains #10's per-measurement provenance, location history, reset command and mode-aware reporting, adding #11's missing console helper, explicit demo loader, all-13 simulation and LIVE-driver declaration/checks. It does not merge either PR or run a database reset.

The [transition/reconciliation record](database-transition-2026-09-27.md) identifies both branch tips, every overlapping file and the commits touching each. The baseline suite had two failures, one a legacy simulated-provenance fallback regression and one an obsolete missing-sensor text assertion; both are corrected in the replacement. Hardware acceptance is still outstanding.


## 27 September 2026 — one fixed FarmPi Android visual identity

### Context

The Android client had accumulated six selectable colour themes from the earlier flexible-learning direction. That no longer matched the current capstone or the FarmPi stakeholder mockup. The theme selector also added settings and visual combinations that did not improve the farm-monitoring task.

### Decision

- Remove the selectable Neutral, NZ red/white/blue, Green/natural, Dark high contrast, Yellow/black and Muted themes from the Android client.
- Use one fixed light FarmPi visual system based on the supplied reference image: white/off-white backgrounds, white cards, dark readable text, restrained FarmPi green for primary actions/selection, rounded surfaces and light grey structure.
- Use semantic status colours consistently: green for current/online/in-sync, amber for old/stale/pending, red for missing/error/unavailable, and blue for simulated/prototype states.
- Keep compact/standard/large text size because text scaling is an accessibility/usability control rather than a cosmetic skin.
- Keep explanation depth, guidance and voice behaviour as independent functional preferences.
- Leave any previously stored theme preference untouched but stop reading or writing it. This avoids an unnecessary preference migration while ensuring installed clients use the same current visual identity.
- Do not change navigation, API behaviour, data authority or backend contracts as part of the theme refactor.

### Evidence boundary

This is a presentation and usability refactor. It does not prove that the reference-image dashboard data cards or tablet layout have been implemented, and it does not change any FarmPi readings, calculations, provenance or acceptance state. Device-level visual acceptance is still required across phone/tablet sizes and the retained text-size choices.
