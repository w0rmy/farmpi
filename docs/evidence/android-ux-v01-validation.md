# FarmPi Android UX v0.1 — validation and handoff

27 September 2026. Work performed directly in `F:\FarmPi`; no commit or push was made. Existing tracked build outputs were preserved by building a separate temporary source copy.

## Implemented

- FarmPi now uses one fixed light visual system: white/off-white surfaces, dark text, restrained green accents, rounded cards and semantic status colours. Previously saved theme values are ignored rather than migrated. App text size continues to respect the device's accessibility font scaling.
- Dashboard / Compare / Ask FarmPi / Alerts / More navigation, with Location Detail, History, Nodes and System Status destinations.
- Dashboard/location requests, comparison controls and history controls call the existing authoritative Ask API and render answers, graphs and evidence in their own native screens. These requests are independent of the Ask conversation.
- Ask retains bounded backend conversation context and now shows up to eight previous exchanges with inspectable sources/charts. Current source category and reading timestamps are visible. Old evidence is cleared when new requests start. Speech normalization, Heard/Interpreted, TTS and a globally accessible Stop speaking control remain.
- Nodes main screen contains compact cards and access controls. Selecting a card opens Node Detail. Registration, farmer locations and OFF/SIMULATED/LIVE sensor modes use the existing administrator API and optimistic configuration fingerprint. LIVE is selectable only when the node advertises a supported physical driver. Hardware/configuration diagnostics are behind Technical details. No online status is invented from timestamps.
- System Status uses the existing database and AI availability fields rather than equating a running application with healthy dependencies.
- Historical graph positions now reflect actual UTC time intervals instead of equal spacing. Dots are the default to avoid implying continuous coverage. Non-finite samples do not affect chart statistics or get joined by lines. Optional line/area modes explicitly disclose their continuity limitation.
- Existing course retirement remains intact; historical documentation and preferences were not erased.

## Deliberately incomplete target features

The current backend does not provide a public structured snapshot, persistent alerts/acknowledgement, threshold editing, or configurable long history windows. Automatic location cards, per-measurement cards, reporting counts, alerts, month/quarter/custom history, automatic discovery, editable server address, and voice-selection/rate settings are explicitly labelled Coming later or Not available yet. Native monitoring panels show real server responses rather than invented values. Current history controls offer one or seven days.

The fixed theme follows the supplied FarmPi stakeholder/reference image as the visual target. The implementation adopts its overall visual language rather than attempting a pixel-for-pixel reproduction. Dedicated tablet navigation remains a follow-up; the current navigation is shared across form factors.

## Validation

- `testDebugUnitTest`, `assembleDebug`, and `lintDebug` passed at the shared/navigation checkpoint and at the monitoring/graph checkpoint.
- Five JVM tests cover the unchanged Ask request contract and UTC/offset/categorical/irregular-time graph positions.
- Final build result and artifact hash are recorded below after packaging.
- Lint reports no errors; existing dependency/API/icon/style warnings remain.
- `git diff --check` passed for source and documentation.
- No device or configured emulator is available. Live backend interaction, TLS trust, voice/TTS, visual phone/tablet layout, large text, disconnected recovery and node approval/configuration require device acceptance. Compilation and unit tests do not establish those results.

## Reproducing the local build

Use JDK 21 and the installed SDK configured in `local.properties`. Copy `clients/android` to a temporary build directory excluding `build`, `.gradle` and `.kotlin` so that tracked outputs in this repository are not overwritten.

Java initially failed before compilation with `Unable to establish loopback connection`. The stack identified Unix-domain socket creation; a short temporary socket directory resolved it:

```powershell
New-Item -ItemType Directory -Force F:\FarmPi\.ux-tmp
$env:JAVA_TOOL_OPTIONS = '-Djdk.net.unixdomain.tmpdir=F:\FarmPi\.ux-tmp'
.\gradlew.bat testDebugUnitTest assembleDebug lintDebug --no-daemon --console=plain
```

The initially missing `org.json` test dependency was downloaded successfully. Subsequent validation ran offline using the populated cache.

## Device acceptance before release

Install the supplied debug APK on a test device with FarmPi certificate trust. Check existing preferences on upgrade; all primary and secondary destinations; current/old/missing/unavailable and simulated responses; comparisons and irregular history; typed/spoken follow-ups, corrections and Stop speaking; request failures versus disconnection; node registration followed by OFF/SIMULATED mode changes, LIVE-driver gating, location edits, pending-to-in-sync acknowledgement and configuration conflict recovery. Check narrow phones, tablets and all text sizes under the fixed FarmPi theme. Device acceptance must deliberately use a test node/configuration; automated UI/unit validation does not itself prove that a physical node applied the requested mode.

## Final packaged checkpoint

Final command completed successfully in 51 seconds: `testDebugUnitTest assembleDebug lintDebug`.

- Tests: 5 passed, 0 failed.
- Lint: 0 errors, 11 warnings, 1 hint (dependency/target/icon and preference-style items).
- APK SHA-256: `7093E69108E644B1E863CEA6E54ABFD9D7F5BB99DEBF998975F919A4603A05CD`.
- APK and original test/lint reports are saved in the task's `outputs/farmpi-android-ux-v01` directory.
- Source and documentation whitespace checks passed. Backend source and endpoint/request contracts were not modified.
- This is a build-validated local prototype checkpoint, not completed device acceptance or a release.
