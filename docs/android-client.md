# Native Android client

## Role

`clients/android` is the primary learner-facing Kotlin/Jetpack Compose client. It calls the FarmPi APIs directly and is not a WebView. The server-rendered browser page remains a diagnostic fallback.

The Android app deliberately performs presentation and device I/O only. It does not query MariaDB, select farm operations, calculate analytics/charts, authorise renames, or invent source provenance.

## Implemented experience

- typed questions and a large speech-recognition control;
- up to five Android speech alternatives sent to FarmPi's deterministic normaliser;
- Heard and Interpreted display when FarmPi corrects a spoken phrase;
- native text-to-speech with en-NZ preference and English fallback;
- immediate Stop behaviour on the same large button while speech is active;
- robust TTS chunking, state, diagnostics, and pronunciation adjustments for `FarmPi` and `DairyNZ`;
- Ask and Learn tabs, Guide me, and context-sensitive next questions;
- a backend-controlled five-module course with a visible Learn → Try → Ask → Check → Continue pattern, free module navigation, and a recommended return path;
- local-only current-module and Try/check/module progress that survives restart; no learner account, cloud sync, grades, badges, or analytics;
- Return to Module and contextual Learn about this actions that reuse the normal Ask conversation rather than create a second conversation engine;
- backend-supplied line/bar charts and bounded evidence;
- expandable source/provenance display;
- explanation depth and guidance-frequency preferences;
- six presentation themes and compact/standard/large text density behind a top-right settings cog.

## Display flexibility

The settings cog moves secondary controls away from the Ask screen so the current learning interaction remains dominant. Preferences are stored in device-local `SharedPreferences`.

Themes are lightweight Material colour schemes applied consistently across the app:

- neutral/default;
- New Zealand red, white, and blue;
- green/natural;
- dark high contrast;
- yellow/black high visibility;
- muted/low stimulation.

Text size changes Compose font scaling for compact, standard, or large presentation. These options are evidence for Developing Flexible IT Courses - visual flexibility, readability, contrast preference, cognitive comfort, and learner adaptation - rather than a separate graphics project. They do not change any answer fact, evidence, operation, or learning objective.

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

If the voice is unavailable, install/enable an English TTS engine and voice in Android settings, then inspect the UI status and Logcat tag. The visible response remains usable even when speech fails.

## HTTPS and certificate trust

The default base URL is `https://farmpi.local/`. The app does not disable certificate validation. `network_security_config.xml` permits the system trust store and a user-installed public CA for `farmpi.local`.

For a test device:

1. confirm `farmpi.local` resolves to the Pi;
2. copy only Caddy's public local root certificate to the device;
3. install it through Android security settings;
4. verify the certificate served by Caddy includes `farmpi.local`;
5. open the app and confirm `/api/status` reports the expected dependencies.

Never distribute Caddy's private CA key, database credentials, or the ESP32 ingest token. A production-distributed app should use a documented certificate lifecycle, potentially bundling only a dedicated public trust anchor in `res/raw`.

## API use

- `GET /api/status` checks connection/dependency health.
- `GET /api/guidance` loads reviewed onboarding and suggestions.
- `GET /api/learning/course` loads the reviewed aim, outcomes, modules, Try/check metadata, and context-to-module mappings.
- `POST /api/speech/normalize` normalises spoken alternatives.
- `POST /api/ask` is the single conversation contract. A course launch supplies only the reviewed `course_module_id`; the server validates it and never accepts client-provided course prompt text.

Android displays the detailed answer and speaks `spoken_answer`. It renders server-provided charts, evidence, source category/tier, and provenance. Backend error details are surfaced when safe; connection/certificate failures remain distinct from a valid FarmPi request that could not be completed.

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
- all six themes remain readable across Ask, Learn, settings, cards, charts, and navigation;
- compact/standard/large text does not clip controls or evidence;
- settings survive process restart;
- the course loads, all five modules are reachable, the recommended sequence and free navigation both work, and local progress survives restart;
- Try completion is recognised after its real response intent, Check remains a self-reflection rather than a grade, and Return to Module preserves the active module after follow-ups;
- course quick actions retain module context; contextual Learn about this links open the relevant module;
- sources/evidence remain inspectable and are not calculated by the phone;
- certificate failure remains visible and no insecure trust bypass exists.
