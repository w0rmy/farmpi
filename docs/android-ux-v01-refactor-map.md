# FarmPi Android UX v0.1 — local refactor map

Audit: 27 September 2026. Local source in F:\FarmPi. Existing source changes: none; generated build outputs already dirty and must be preserved.

| Target | Current implementation | Refactor |
|---|---|---|
| Design system | Multiple selectable themes | One fixed FarmPi light theme: white/off-white surfaces, green accents, rounded cards and semantic status chips; retain text-size accessibility choices |
| Navigation | Ask / Nodes | Dashboard, Compare, Ask FarmPi, Alerts, More; secondary History, Nodes, Settings, System Status |
| Dashboard / Location | Earlier version depended on conversational queries for current-state display | Structured `/api/monitoring/overview`, measurement icons/cards, location cards, age/provenance display, compact soil-moisture sparkline and verified 24-hour featured chart |
| Compare / History | Verified charts within Ask | Dedicated query controls using existing Ask contract; retain chart/provenance; seven-day backend limit, longer periods labelled Coming later |
| Ask FarmPi | Single response, speech, TTS, evidence | Chat presentation, visible source context, retain corrections and speech controls; clear old evidence when a new request starts |
| Alerts | No alert API | Target filters and threshold panel with explicit Coming later; no fake alerts |
| Nodes | All configuration forms inline | Compact cards, separate detail/settings and pending registration; preserve approval/configuration payloads and fingerprint checks |
| Settings / Status | Preferences dialog, Boolean server check | Keep preferences, expose server and voice information; report only actual health fields |
| Learn | Already removed from source | Keep historical evidence and preference store intact |

Authority: no new backend endpoints or fabricated readings, freshness, counts, node online status or health. Preserve TLS, session-only admin token, conversation IDs, request preferences, voice normalization, TTS and provenance. No GitHub push.

Visual direction: use the supplied FarmPi reference image as the style target rather than supporting selectable skins. Keep the existing functional navigation and data authority while applying the white/off-white, dark-text, green-accent visual identity consistently.

Validation: compile and JVM request tests after shared/navigation changes and final screens; lint at final checkpoint. Device checks require an available emulator/device. Build in a temporary source copy to avoid overwriting pre-existing tracked build outputs.

## Local implementation outcome

The map above preceded implementation. The resulting source includes MonitoringUi.kt (native operational screens and source summaries), GraphData.kt (UTC time-axis helpers), updated shared/navigation/chat code, and separate Nodes/Node Detail. Compare and History now display results locally rather than routing every request into Ask. See [validation and remaining acceptance](evidence/android-ux-v01-validation.md) for implemented versus planned scope and the build workaround.
