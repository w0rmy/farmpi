# FarmPi development record

This record captures material design decisions and their outcome/evidence rationale. Current operating instructions live in the subject guides; historical performance measurements live under `docs/history`.

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
