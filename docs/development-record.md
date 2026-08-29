# FarmPi development record

This record captures material design decisions and their outcome/evidence rationale. Current operating instructions live in the subject guides; historical performance measurements live under `docs/history`.

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
