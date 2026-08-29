# FarmPi development record

This record captures material design decisions and their outcome/evidence rationale. Current operating instructions live in the subject guides; historical performance measurements live under `docs/history`.

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
