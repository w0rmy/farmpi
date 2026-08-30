# Testing, evaluation, and capstone evidence

FarmPi needs two kinds of assurance: software verification and evidence that the embedded learning platform supports the defined outcomes. Passing tests does not prove learning effectiveness, and learner feedback does not replace deterministic data tests.

## Automated backend checks

From the repository root, with the project virtual environment active:

```bash
python -m unittest discover -s tests -v
python -m compileall -q app tests
```

The suite covers measurement validation, telemetry time/sequence behaviour, database operations, deterministic analytics, paddock identity and rename confirmation, speech normalisation, semantic interpretation, source hierarchy, LLM compatibility, response provenance, fallback behaviour, and the course contract (unique IDs, outcome/next-module/intents mappings, deterministic payload, invalid module rejection, and controlled reviewed prompt context). Add a controlled fixture whenever a new calculation, route, source claim, or state-changing operation is introduced.

Farm facts must be testable without an LLM. Tests for current readings, history, comparisons, device state, timestamps, and calculations must assert exact deterministic results and must not substitute generated text for database evidence.

## Android checks

Build the debug client from `clients/android`:

```powershell
.\gradlew.bat :app:assembleDebug
```

Then test on a device that trusts the FarmPi development certificate. Check text and speech input, visible and spoken output, TTS stop/retry behaviour, charts, evidence/provenance, all six themes, compact/standard/large text size, preference persistence, and operation when TTS is unavailable. Exercise both portrait and landscape layouts and at least one small display.

For the course, confirm that it loads, every one of the five modules opens, the recommended sequence and direct navigation both work, progress survives a restart, a matching real response marks a Try complete, and Check is not represented as a grade. Launch Try/Ask, ask several quick/follow-up questions, use Return to Module, and confirm the original module remains active. Check contextual Learn about this links, evidence/source inspection, all themes and text sizes on the course screens, and portrait/landscape/small-screen behaviour.

For Module 1 specifically, start from a connected client without changing any connection configuration. Move between Ask and Learn; identify the settings cog and connection-status message; type “What can FarmPi help me with?”; ask another question by microphone; and stop spoken output. Use Guide me, select a suggested question and a follow-up. In Settings, change text size and theme, compare Simple and Technical explanation depth with similar questions, and retain a preferred configuration. Confirm the Check remains practical and ungraded, asks what to change when an explanation is too technical and what to use when no next question is clear, and that Continue opens Module 2.

## Raspberry Pi deployment checks

After install or update:

```bash
sudo systemctl is-active mariadb farmpi-llm farmpi caddy
curl -fsS http://127.0.0.1:8000/health
curl -fsS http://127.0.0.1:8000/api/status
curl --resolve farmpi.local:443:127.0.0.1 -k https://farmpi.local/health
```

Also submit one authenticated ingest sample, retry the same sensor/sequence to confirm deduplication, ask for its exact value, request a historical calculation, test an unrelated general question, and verify that a stopped database or LLM is described honestly. Do not record credentials in test output or evidence documents.

## Requirements traceability

Every material change should link implementation, verification, and outcome evidence:

| Concern | Required evidence |
|---|---|
| Farm facts and calculations | exact fixtures, provenance fields, failure-path tests |
| Source selection | tier/category assertions and reviewed claim/source records |
| General conversation | useful-answer and uncertainty checks without invented farm facts |
| State-changing actions | validation, confirmation, identity, and audit tests |
| Flexible presentation | theme, contrast, text size, persistence, and usability observations |
| Learning interaction | task observation, explanation-depth comparison, and source comprehension |
| Deployment | recorded service/health checks and version/configuration used |

## Learner evaluation

Use a small, consented group of nontechnical participants. Do not fabricate results. Observe whether they can:

- begin using FarmPi without learning a command language;
- ask a current-value and historical/comparison question in their own words;
- distinguish FarmPi evidence from external guidance and general explanation;
- recognise when farm evidence is unavailable;
- use evidence/charts to explain an answer;
- adjust explanation depth, guidance, theme, and text size;
- recover from a speech or paddock-name misunderstanding;
- complete a teach-by-doing activity and identify what they learned.

Record task completion, hesitation/confusion, source comprehension, accessibility/preferences, participant comments with consent, and resulting design actions. Do not claim agronomic effectiveness, accessibility compliance, or learning gains without suitable evidence.

## Performance evaluation

Record end-to-end latency and the existing response timing stages under a named hardware/model/configuration. Compare deterministic direct answers separately from model-assisted explanations. Model size, tokens per second, and memory are implementation evidence; they are not the capstone thesis. Historical model measurements belong in [Local LLM evaluation history](history/local-llm-evaluation.md).

## Documentation release check

Before publishing a material change:

1. update the owning guide and affected Mermaid source;
2. remove or archive superseded current-state text;
3. check local Markdown links and documented paths;
4. compare commands, environment names, endpoints, and defaults with code/configuration;
5. run automated checks and record any limitation honestly;
6. apply the [capstone outcome gate](capstone-governance.md).
