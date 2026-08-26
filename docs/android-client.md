# Native Android client

`clients/android/` is a Kotlin/Jetpack Compose Android Studio project: a thin native client for FarmPi's APIs, not a WebView wrapper. The existing browser UI remains a diagnostic/fallback interface.

The first milestone provides FarmPi status, typed input, a large native `SpeechRecognizer` control (up to five alternatives), native `TextToSpeech`, conversation display, Guide me/suggestions, Heard versus Interpreted speech display, explanation depth, guidance frequency, and a small Learn tab. Speech alternatives are sent to `POST /api/speech/normalize`; FarmPi's existing deterministic server-side normalizer selects/corrects farm language before `POST /api/ask`. Typed text bypasses normalization.

The app uses only HTTPS (`https://farmpi.local/` by default). It does not install a permissive trust manager or disable certificate checks. The included network-security configuration explicitly permits a user-installed FarmPi/Caddy local CA for `farmpi.local`; install the public local CA certificate through Android Settings on each test device, then confirm the Caddy certificate includes `farmpi.local`. Do not copy a CA private key or Wi-Fi/ingest secret into the project. A deployment that distributes the app may instead bundle the public CA in `res/raw` and replace the `user` trust anchor with that resource after normal certificate rotation procedures are defined.

Open `clients/android` in Android Studio with JDK 17, allow Gradle to sync, then select an Android device on the FarmPi LAN and run `app`. The project uses current Compose/AGP declarations; it has no checked-in Gradle wrapper binary, so Android Studio's configured Gradle/JDK is the supported local build path for this scaffold.
