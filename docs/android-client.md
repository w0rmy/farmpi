# Native Android client

`clients/android/` is a Kotlin/Jetpack Compose Android Studio project: a thin native client for FarmPi's APIs, not a WebView wrapper. The existing browser UI remains a diagnostic/fallback interface.

The initial learner client provides FarmPi status, typed input, a large native `SpeechRecognizer` control (up to five alternatives), native `TextToSpeech`, conversation display, Guide me/suggestions, Heard versus Interpreted speech display, explanation depth, guidance frequency, and a teach-by-doing Learn tab. It renders the backend's compact native bar/time-series chart payloads and can reveal the bounded evidence/data list; charts are never calculated on the phone. Explanation and guidance preferences are saved in device-local `SharedPreferences`, not in a learner account. The purpose-built FarmPi palette uses neutral charcoal surfaces with restrained green/grey accents rather than default pink/purple Material colours.

The top-right settings cog moves secondary controls off the Ask screen to reduce cognitive load. It contains explanation depth, guidance frequency, six whole-app presentation presets (neutral, NZ red/white/blue, green/natural, dark high-contrast, yellow/black high-visibility, muted/low-stimulation), and compact/standard/large text density. These options apply consistently through Compose `MaterialTheme` and local display density, are stored in `SharedPreferences`, and never alter the facts or operations FarmPi exposes. They are bounded visual-flexibility evidence for Developing Flexible IT Courses - readability, contrast preference, cognitive comfort and learner adaptation - rather than an Android graphics or animation workstream.

Speech alternatives are sent to `POST /api/speech/normalize`; FarmPi's existing deterministic server-side normalizer selects/corrects farm language before `POST /api/ask`. Typed text bypasses normalization. `POST /api/ask` is the single conversational contract; it may contain `answer`, `spoken_answer`, `intent`, suggestions, chart, evidence, source category, and speech-normalisation details. Android displays the detailed answer but speaks the concise `spoken_answer`, keeping precise timestamps and routine simulation provenance in the visual evidence path.

The current client understands observational, educational and combined source categories. The 27 August 2026 learning architecture requires the contract/UI to expand, when those capabilities are implemented, to distinguish a FarmPi observation, deterministic calculation, curated authoritative New Zealand guidance, external research and general agricultural explanation. The app must not make a researched or general explanation look like a sensor fact; source, uncertainty and any supporting link should remain inspectable without making normal spoken answers cumbersome.

The app uses only HTTPS (`https://farmpi.local/` by default). It does not install a permissive trust manager or disable certificate checks. The included network-security configuration explicitly permits a user-installed FarmPi/Caddy local CA for `farmpi.local`; install the public local CA certificate through Android Settings on each test device, then confirm the Caddy certificate includes `farmpi.local`. Do not copy a CA private key or Wi-Fi/ingest secret into the project. A deployment that distributes the app may instead bundle the public CA in `res/raw` and replace the `user` trust anchor with that resource after normal certificate rotation procedures are defined.

## Android Studio build prerequisites

Open `clients/android` as the Android Studio project. The supported build toolchain is:

- Android Studio Panda 3 (2025.3.3) Patch 1 or newer, with Android SDK Platform 37 and Android SDK Build-Tools 36.0.0 installed (Android Studio normally installs the build tools automatically).
- JDK 17 or newer (the JDK bundled with a compatible Android Studio release is suitable).
- Android Gradle Plugin 9.1.1 and Gradle 9.3.1 (the checked-in Gradle wrapper selects the required Gradle version).
- AGP 9's built-in Kotlin support and the Compose compiler Gradle plugin 2.3.21. Do not add the legacy `org.jetbrains.kotlin.android` plugin: AGP 9 rejects it.

The app compiles with `compileSdk = 37`, but intentionally retains `targetSdk = 36` and `minSdk = 26`; installing Platform 37 does not alter the runtime behavior the app opts into. Compose dependencies are managed exclusively by the stable Compose BOM `2026.08.00`; individual Compose libraries intentionally have no explicit versions. `activity-compose:1.13.0` supplies `setContent` for the `ComponentActivity` entry point.

In Android Studio, install **Android SDK Platform 37** in SDK Manager if it is not already present, set the Gradle JDK to 17 or newer, sync the project, then use **Build > Make Project** (or run the `app` configuration). From a terminal, run `./gradlew assembleDebug` on macOS/Linux or `gradlew.bat assembleDebug` on Windows.
