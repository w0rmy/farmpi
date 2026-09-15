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
- explanation-depth and guidance-frequency preferences;
- six presentation themes and compact/standard/large text-size choices;
- bounded conversation continuity supplied by the backend;
- visible connection/dependency status and differentiated request/connection failures.

## Legacy learning UI

The current build still contains the **Learn** tab and the five-module course created for the earlier **Developing Flexible IT Courses** elective. It remains functional and is useful development history, but it is no longer the primary capstone requirement.

Do not expand the course, progress model, or learning-specific UI unless a current application requirement justifies it. A later mobile-interface redesign may de-emphasise or remove these surfaces after the functional requirements are reviewed.

## Display and mobile usability

The settings cog keeps secondary controls away from the main Ask interaction. Preferences are stored in device-local `SharedPreferences`.

Themes are lightweight Material colour schemes applied consistently across the app:

- neutral/default;
- New Zealand red, white, and blue;
- green/natural;
- dark high contrast;
- yellow/black high visibility;
- muted/low stimulation.

Text size changes Compose font scaling for compact, standard, or large presentation. Under the current project direction these are treated as **mobile usability and presentation features**, not as evidence for a flexible-learning elective. They must not change answer facts, graph values, evidence, or operations.

Current mobile work should favour a clear phone interface, readable graph cards, obvious recovery/error states, and low interaction cost rather than adding presentation options for their own sake.

## Graph presentation

The Android client receives verified chart payloads from the backend and chooses only how to display them.

- time-series data can be viewed as line, area, bars, or dots;
- light/lux defaults to an area-style **Day profile** view;
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

Legacy endpoints retained from the earlier course direction:

- `GET /api/learning/course`;
- `GET /api/learning/activities`;
- optional `course_module_id` on `/api/ask`.

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
- all six themes remain readable across primary screens, cards, charts, navigation, and settings;
- compact/standard/large text does not clip controls or evidence;
- settings survive process restart;
- sources/evidence remain inspectable and are not calculated by the phone;
- certificate failure remains visible and no insecure trust bypass exists;
- portrait, landscape, and at least one small phone display remain usable.

Legacy Learn/course features should continue to avoid crashes while they remain in the build, but they are not the primary acceptance target for the current capstone direction.
