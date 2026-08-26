# Native Android client

`clients/android/` is a Kotlin/Jetpack Compose Android Studio project: a thin native client for FarmPi's APIs, not a WebView wrapper. The existing browser UI remains a diagnostic/fallback interface.

The initial learner client provides FarmPi status, typed input, a large native `SpeechRecognizer` control (up to five alternatives), native `TextToSpeech`, conversation display, Guide me/suggestions, Heard versus Interpreted speech display, explanation depth, guidance frequency, and a teach-by-doing Learn tab. It renders the backend's compact native bar/time-series chart payloads and can reveal the bounded evidence/data list; charts are never calculated on the phone. Explanation and guidance preferences are saved in device-local `SharedPreferences`, not in a learner account.

Speech alternatives are sent to `POST /api/speech/normalize`; FarmPi's existing deterministic server-side normalizer selects/corrects farm language before `POST /api/ask`. Typed text bypasses normalization. `POST /api/ask` is the single conversational contract; it may contain `answer`, `intent`, suggestions, chart, evidence, source category, and speech-normalisation details.

The app uses only HTTPS (`https://farmpi.local/` by default). It does not install a permissive trust manager or disable certificate checks. The included network-security configuration explicitly permits a user-installed FarmPi/Caddy local CA for `farmpi.local`; install the public local CA certificate through Android Settings on each test device, then confirm the Caddy certificate includes `farmpi.local`. Do not copy a CA private key or Wi-Fi/ingest secret into the project. A deployment that distributes the app may instead bundle the public CA in `res/raw` and replace the `user` trust anchor with that resource after normal certificate rotation procedures are defined.

## Android Studio build prerequisites

Open `clients/android` as the Android Studio project. The supported build toolchain is:

- Android Studio Panda 3 (2025.3.3) Patch 1 or newer, with Android SDK Platform 37 and Android SDK Build-Tools 36.0.0 installed (Android Studio normally installs the build tools automatically).
- JDK 17 or newer (the JDK bundled with a compatible Android Studio release is suitable).
- Android Gradle Plugin 9.1.1 and Gradle 9.3.1 (the checked-in Gradle wrapper selects the required Gradle version).
- AGP 9's built-in Kotlin support and the Compose compiler Gradle plugin 2.3.21. Do not add the legacy `org.jetbrains.kotlin.android` plugin: AGP 9 rejects it.

The app compiles with `compileSdk = 37`, but intentionally retains `targetSdk = 36` and `minSdk = 26`; installing Platform 37 does not alter the runtime behavior the app opts into. Compose dependencies are managed exclusively by the stable Compose BOM `2026.08.00`; individual Compose libraries intentionally have no explicit versions. `activity-compose:1.13.0` supplies `setContent` for the `ComponentActivity` entry point.

In Android Studio, install **Android SDK Platform 37** in SDK Manager if it is not already present, set the Gradle JDK to 17 or newer, sync the project, then use **Build > Make Project** (or run the `app` configuration). From a terminal, run `./gradlew assembleDebug` on macOS/Linux or `gradlew.bat assembleDebug` on Windows.
