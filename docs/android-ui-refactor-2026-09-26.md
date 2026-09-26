# Android UI retirement audit — 26 September 2026

Base: `333ed91` (current main at the start of this change).
Branch: `refactor/android-monitoring-ui`.

## Dependency audit and plan

The native app has Ask, Learn and Nodes destinations, selected by two booleans. Ask owns monitoring responses and graphs; there is no independent native Dashboard. Settings are a global dialog. Ask response, speech, conversation and display state live above the destination switch. Nodes owns its administration state and uses shared API transport functions.

Learn couples into Ask through eight course state values, a course fetch effect, persisted learning progress, activity callbacks, module return links, response-intent matching and the optional `course_module_id` request field. CourseUi.kt contains only course presentation/models. GraphVisuals.kt and NodesUi.kt have no course dependency.

Plan: remove Learn and its callback/state/API dependency chain, reduce navigation to Ask/Nodes, retain monitoring and contextual explanation, preserve the existing preference store, and leave backend contracts and historical documents for a separate consumer audit. Do not migrate or erase old course preferences: ignoring them preserves upgrade settings and historical data without restoring course navigation.

## Implemented boundary

Removed CourseUi.kt and the course-only state, parsing, network fetch, progress updates and UI links from MainActivity. All question entry paths still share Ask, speech normalization and bounded conversation continuity. A small request builder makes the no-module request contract executable in JVM tests. Settings, source display, chart rendering, Nodes administration and TTS implementation remain in place. Current Android documentation/diagram now describe the implemented two-tab navigation.

No backend code or historical course documentation was changed. No generated build outputs are part of this change. The repository already tracks Android build outputs, so validation uses a separate temporary copy excluding those outputs.

## Validation

- Backend: `.venv/Scripts/python.exe -m unittest discover -s tests`: **146 tests passed**.
- `git diff --check`: passed.
- Android source audit: no Course models, Learn destination, progress reads/writes, course endpoint or module request field remains in production sources.
- Added two JVM request contract tests: first question preserves preferences without conversation/module fields; follow-up preserves conversation context without module fields.
- Attempted `testDebugUnitTest assembleDebug lintDebug` using Gradle 9.3.1, installed SDK at D:/Android/SDK and JDK 25, then JDK 21. Both fail before compilation with `java.io.IOException: Unable to establish loopback connection`. The detailed stack reports `SocketException: Invalid argument: connect` while opening the JVM selector pipe. An IPv4 retry also failed. **Android tests, compilation and lint have not passed; no new APK is claimed.**
- The initial backend attempt using the system Python lacked FastAPI; rerunning with the repository environment passed the complete suite.

## Remaining acceptance

On a build-capable host run `testDebugUnitTest assembleDebug lintDebug`. On a device, upgrade over saved course progress and verify only Ask/Nodes appear; settings survive; typed/spoken/suggested questions and contextual follow-ups work; graphs and provenance remain available; speech stops correctly; request and connection failures remain distinct; switching tabs retains Ask responses; Nodes discovery, registration, configuration and sync display still work. Exercise all themes, text sizes and a small screen. These device checks were not performed in this session.
