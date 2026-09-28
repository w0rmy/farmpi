# Native Android client

## Role

`clients/android` is the primary user-facing Kotlin/Jetpack Compose client. It calls the FarmPi APIs directly and is not a WebView. The server-rendered browser page remains a diagnostic fallback.

The Android app deliberately performs presentation and device I/O only. It does not query MariaDB, select farm operations, calculate analytics/chart values, authorise renames, or invent source provenance.

The current capstone direction evaluates the Android client as part of a functional integrated application: usability, state handling, API integration, voice/TTS behaviour, graph presentation, error recovery, and mobile layout are now stronger evidence than the earlier embedded-course design.

## Implemented application experience

- typed questions and a large speech-recognition control;
- up to five Android speech alternatives sent to FarmPi's deterministic normaliser;
- Heard and Interpreted display when FarmPi corrects a spoken phrase;
- native text-to-speech with en-NZ preference and English fallback;
- immediate Stop behaviour on the same large button while speech is active;
- robust TTS chunking, state, diagnostics, and pronunciation adjustments for `FarmPi` and `DairyNZ`;
- Ask tab, Guide me, and context-sensitive next questions;
- backend-supplied chart data rendered as interactive line, area/day-profile, bars, or dots where appropriate;
- low/latest/high chart summaries and time labels;
- expandable source/provenance display;
- working AI response-detail and follow-up-guidance preferences, plus text-size accessibility controls;
- one fixed FarmPi light visual system with compact/standard/large text-size choices;
- bounded conversation continuity supplied by the backend;
- visible connection/dependency status and differentiated request/connection failures;
- a Nodes administration screen for pending discovery, explicit registration, farmer-defined location assignment, stable node identity, desired/applied configuration state, editable per-sensor OFF/SIMULATED/LIVE modes and runtime reporting state. Android submits the complete supported mode map with the current expected fingerprint, so stale edits are rejected rather than overwriting a newer configuration.

## Navigation after course retirement

The Android client opens Dashboard with primary destinations **Dashboard / Compare / Ask FarmPi / Alerts / More**. More opens History, Nodes, Settings and System Status. Dashboard and Location Detail use the deterministic `/api/monitoring/overview` contract for current-state cards, location cards, age and provenance metadata. Full graphs are intentionally kept out of the Dashboard: tapping a graphable measurement opens History preselected to that measurement and scope, while tapping a farmer-named location opens Location Detail and each graphable measurement there opens that location's trend. Compare loads configured farmer locations into drop-down selectors and calls `/api/monitoring/compare` with the two stable location IDs, so the selected pair is compared without LLM interpretation. History supports 6-hour, 1-day and 7-day views over the existing deterministic Ask/analytics contract. Alerts and thresholds remain explicitly unavailable prototypes. Nodes shows compact cards; configuration and registration live on a separate Node Detail page. See [the UX v0.1 refactor map](android-ux-v01-refactor-map.md).

Learn, module navigation, Try/Check/Continue, progress, Return to Module and course quick actions have been removed, together with their Android models and API parsing. All questions omit `course_module_id`; contextual explanations, Guide me and ordinary conversation continuity remain.

The existing `farmpi-learning` preference store is retained to preserve explanation, guidance and text-size settings. Historical `learning_*` and saved `theme` keys are left untouched but are no longer read or written by the client. Course documentation and earlier development records remain historical evidence. Backend course contracts remain available pending a separate consumer audit.

## Display and mobile usability

The Settings screen now contains only controls that are useful in the current local FarmPi application. AI response detail, follow-up guidance and text size are stored in device-local `SharedPreferences`. Voice is shown as live Android status information rather than as a fake configuration panel. The FarmPi server address is fixed by the local installation and is not displayed or editable as a user preference.

FarmPi now uses one fixed light visual system based on the current stakeholder/mockup direction: white and off-white surfaces, dark readable text, restrained FarmPi green for primary actions and selection, rounded cards, light grey dividers, and semantic status colours. Current/online/in-sync states use green, old/stale/pending states use amber, missing/error/unavailable states use red, and simulated/prototype states use blue. Theme selection has been removed so the application presents one coherent identity.

Text size still multiplies the device accessibility font scale for compact, standard, or large presentation. Explanation depth, guidance and voice behaviour remain independent settings. These presentation choices must not change answer facts, graph values, evidence, or operations.

Current mobile work should favour a clear phone interface, readable graph cards, obvious recovery/error states, and low interaction cost rather than adding cosmetic presentation options.

The retained settings have verified plumbing:
- `explanation` is sent as `preferences.explanation_level` on every Ask request. The backend accepts `simple / normal / technical`, uses it when rendering reviewed concepts, and places the requested level into the governed LLM system context.
- `guidance` is sent as `preferences.guidance_level` on Ask and as `guidance_level` for Guide me. The backend uses `more / normal / less` to vary suggested next questions.
- `display_density` remains Android presentation-only and never enters the FarmPi data/AI request contract.
- voice input/read-aloud use Android SpeechRecognizer/TextToSpeech. The Settings screen reports current voice status but does not pretend to offer voice/rate controls that are not implemented.

## Graphical dashboard

The monitoring UI now has a reusable visual layer rather than relying on text cards alone:

- Material vector icons map measurement keys to recognisable visual cues such as moisture, temperature, light, pressure and wind;
- farm-summary measurement cards show formatted values, source mode and reading age;
- Dashboard measurement cards deliberately show current values without embedded sparklines or a duplicated full soil-moisture graph;
- tapping a graphable farm-summary measurement opens History directly for that farm-wide measurement;
- farmer-named location cards show up to three latest measurements and open Location Detail;
- Location Detail reuses the same measurement-card system, and tapping a graphable measurement opens its recent trend for that configured location;
- History exposes the graphable catalogue measurements and 6-hour, 1-day and 7-day time windows; wind direction remains current-only because ordinary linear historical averaging is not defined for circular direction data.

Icons are measurement labels, not weather claims. For example, a sun icon denotes the light/lux measurement; it does not mean FarmPi has classified the weather as sunny.

## Graph presentation

The Android client receives verified chart payloads from the backend and chooses only how to display them.

- time-series data can be viewed as line, area, bars, or dots;
- time series default to a labelled line view with timestamp-proportional spacing; Dots remains available for inspecting individual observations, and Day profile/Area remain presentation alternatives with an explicit continuity limitation;
- comparison datasets can be viewed as bars or dots;
- changing display mode must not change any underlying value;
- farm-wide, named-paddock, and cross-paddock comparisons are separate backend meanings even if they use the same renderer.

The phone must never infer or fabricate missing chart values locally.

## Voice behaviour and diagnostics

Speech recognition uses `en-NZ`, free-form language, and up to five alternatives. FarmPi's server-side normaliser decides whether an alternative is meaningfully more farm-consistent. Typed input bypasses normalisation.

Text-to-speech:

1. initialises the Android TTS engine;
2. prefers an installed `en-NZ` voice, then any English voice;
3. converts `FarmPi` to `Farm Pi` and `DairyNZ` to `Dairy en zed` for clearer speech;
4. splits long responses into safe chunks and queues them in order;
5. cancels recognition before playback so STT and TTS do not compete;
6. cancels existing speech before a new question or Guide me request;
7. exposes readiness, selected locale/voice, queue state, completion, stop, and error status in the UI and Logcat (`FarmPiTTS`).

A previous integration fault allowed JSON `null` for `spoken_answer` to become the literal four-character string `"null"` through Android `JSONObject.optString`. Both server and client now fall back to the visible answer when spoken text is null/blank. This should remain part of regression testing.

If voice is unavailable, the visible response must remain usable.

## Request timeout behaviour

Ordinary local API calls retain a 30-second read timeout. `/api/ask` has a separate 130-second read window because a genuine Pi-local language-model explanation may take longer than a database or monitoring request. A response timeout is reported as a processing timeout, not as a certificate or FarmLAN failure. Deterministic dashboard and comparison operations do not depend on that longer LLM window.

Farmer-defined names such as `Bob's paddock` and `Fred's paddock` are treated as location names. Summary questions such as `What stats are available on Fred's paddock?` route directly to the deterministic paddock-summary path with zero LLM generation time. Smart/curly apostrophes from speech input are normalised before location resolution.

## HTTPS and certificate trust

The default base URL is `https://farmpi.local/`. The app does not disable certificate validation. `network_security_config.xml` permits the system trust store and a user-installed public CA for `farmpi.local`.

For a test device:

1. confirm `farmpi.local` resolves to the Pi;
2. copy only Caddy's public local root certificate to the device;
3. install it through Android security settings;
4. verify the certificate served by Caddy includes `farmpi.local`;
5. open the app and confirm `/api/status` reports the expected dependencies.

Never distribute Caddy's private CA key, database credentials, or the ESP32 ingest token.

## API use

Current primary endpoints:

- `GET /api/status` checks connection/dependency health;
- `GET /api/guidance` loads reviewed onboarding/suggestions;
- `POST /api/speech/normalize` normalises spoken alternatives;
- `POST /api/ask` is the main conversation/data-query contract;
- `POST /api/ingest` is used by sensor/simulator clients, not the Android UI.

Managed-node administration used by the Nodes screen includes the node contact/registration/configuration APIs and farmer-location creation described in [S3 node bring-up](s3-node-bringup.md). The main Nodes screen remains a compact list; tapping a card opens that node's detail/settings page. Administrative changes require the separate FarmPi administrator token; it is not the ESP32 ingest token and is held only for the current Nodes screen session.

Legacy endpoints retained from the earlier course direction:

- `GET /api/learning/course`;
- `GET /api/learning/activities`;
- optional `course_module_id` on `/api/ask`.

Android no longer consumes these contracts. Audit other consumers before removing them separately.

The Android client no longer calls the legacy course endpoints or sends module context.

Android displays the detailed answer and speaks `spoken_answer`. It renders server-provided charts, evidence, source category/tier, and provenance. Backend errors should be converted into useful user-facing states; certificate/network failures remain distinct from a valid FarmPi request that could not be completed.

## Build requirements

- an Android Studio release that supports Android Gradle Plugin 9.1.1;
- JDK 17 or newer;
- Android SDK Platform 37;
- Android Gradle Plugin 9.1.1 and Gradle 9.3.1;
- AGP 9 built-in Kotlin support and Compose compiler plugin 2.3.21;
- Compose BOM 2026.08.00 and `activity-compose` 1.13.0.

The application uses `compileSdk=37`, `targetSdk=36`, `minSdk=26`, version code 2, and version name 0.2.0.

Open `clients/android` as the Android Studio project, select a JDK 17+ Gradle runtime, install Platform 37, sync, and use **Build > Make Project**. Command line:

```powershell
cd clients/android
$env:JAVA_HOME = 'C:\Program Files\Android\Android Studio\jbr'
.\gradlew.bat assembleDebug
```

On macOS/Linux use `./gradlew assembleDebug`.

## Manual acceptance checks

- connection status distinguishes backend failure from request failure;
- typed and spoken questions reach the same `/api/ask` contract;
- speech corrections display Heard and Interpreted text;
- a new question stops previous TTS, and Stop cancels playback immediately;
- no JSON null/`"null"` value is spoken;
- current-value, historical, farm-wide, named-paddock, and cross-paddock requests display correctly;
- soil-moisture and light/day-profile graphs work without inventing a paddock when none was requested;
- line/area/bars/dots switches change presentation only, not values;
- unsupported graph requests return a useful capability/alternative message rather than a generic `I cannot create graphs` response;
- the fixed FarmPi theme remains visually consistent across primary screens, cards, charts, navigation, settings and semantic status chips;
- compact/standard/large text does not clip controls or evidence;
- settings survive process restart;
- sources/evidence remain inspectable and are not calculated by the phone;
- certificate failure remains visible and no insecure trust bypass exists;
- Node Detail can switch a supported measurement between OFF and SIMULATED, and can select LIVE only when the firmware advertises a live driver;
- saving a sensor-mode change shows UPDATE PENDING until the ESP32 acknowledges the new fingerprint, then IN SYNC;
- a stale configuration save is rejected and requires a refresh rather than silently overwriting the current desired state;
- portrait, landscape, and at least one small phone display remain usable.

Acceptance must verify that no Learn tab, module link or course quick action is reachable, including on an upgrade with saved course progress. Switch Ask → Nodes → Ask during a request and after a graph response; confirm Ask state survives and Nodes refresh/registration/configuration still work. Verify ordinary follow-ups retain conversation context without a module field.


## Ask FarmPi acceptance cleanup — 28 September 2026

Guide me now receives farmer-configured location names from the backend and builds examples from those names instead of exposing legacy labels such as Paddock B or Paddock 2. Time examples use farmer-readable periods such as 24 hours rather than raw minute counts.

Ask responses keep the answer, source category, optional chart and follow-up questions in the normal reading flow. Raw observation timestamps, sensor identifiers and provenance remain available, but are collapsed behind Supporting details so diagnostic evidence does not push the next interaction off-screen. Simulated results retain a concise visible Simulated status chip.

This is a presentation change only: the client still receives the complete evidence/provenance payload and does not alter FarmPi facts.


## Graph presentation acceptance — 28 September 2026

The full chart component is now treated as presentation/evidence UI rather than a decorative sparkline. It uses the fixed FarmPi visual palette instead of relying on Material defaults, with a neutral green-grey plot surface, FarmPi green/blue/amber/grey series colours, explicit grid/axis lines and a white FarmPi card surface.

Full charts now display:

- a labelled Y axis using the chart title and unit;
- five numeric Y-scale labels tied to the plotted range;
- a labelled X axis using Location for comparisons, Time (UTC) for timestamped history, or Observation for non-time categorical data;
- up to three representative X-axis labels so a screenshot shows the beginning, middle and end of the displayed range;
- Low / Latest / High values above the plot;
- Line as the default time-series view and Bars as the default comparison view.

The visual mode controls still change presentation only; they do not alter the underlying verified values.

For presentation screenshots, verify that axis titles, scale values, X labels and the chart title remain legible at standard text size on the actual target phone/tablet. A screenshot should be understandable without having to infer what either axis represents.


## Measurement drill-down — 28 September 2026

Dashboard is now a current-state surface rather than a mixed current/history screen. It no longer renders the soil-moisture mini sparkline or the duplicate featured soil-moisture graph.

For graphable measurements, the current-value card itself is the affordance: **View trend** opens History with the correct measurement and farm/location scope already selected and immediately requests the 1-day graph. The same pattern is used inside a farmer-named Location Detail page. Users can then switch between 6 hours, 1 day and 7 days or choose another graphable measurement.

The graphable History catalogue includes soil moisture, soil temperature, air temperature, relative humidity, soil pH, soil EC, light, rainfall, barometric pressure, wind speed, pasture height and leaf wetness. Wind direction remains current-only because degrees wrap at 360 and require circular-statistics treatment rather than an ordinary linear historical average.
