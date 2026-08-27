# FarmPi grounding, provenance, and deterministic control

## Purpose

FarmPi uses grounding and guardrails to protect **farm-specific facts and state-changing actions**, not to restrict the learner to a narrow command language.

The important architectural distinction is:

> **The language model may interpret and teach broadly; FarmPi application code remains authoritative for this farm's observations, calculations, identities, database access and mutations.**

Early development applied the same deny-by-default approach to both factual authority and learner language. Testing on 27 August 2026 showed that this was too restrictive for the Flexible IT Training objective. Exact regex routes could return accurate data, but ordinary phrases, polite requests and broader agricultural questions could be rejected or misclassified.

The current architecture therefore keeps the strong data/action boundaries while opening the conversational and educational layers.

## Current control path

```text
ESP32 telemetry / learner question
        ↓
Telemetry validation OR speech/domain normalisation
        ↓
Fast deterministic route where meaning is obvious
        ↓                         ↓
        └──── ambiguous/open wording ────┐
                                         ↓
                              semantic intent interpreter
                                         ↓
                              structured reviewed intent
                                         ↓
                     deterministic application execution
                         ├─ paddock resolver
                         ├─ MariaDB retrieval
                         ├─ deterministic analytics
                         └─ explicit mutation confirmation
                                         ↓
                     provenance-labelled knowledge context
                         ├─ FarmPi observation
                         ├─ FarmPi calculation
                         ├─ curated NZ source material
                         └─ general agricultural explanation
                                         ↓
                             concise teaching response
```

The semantic interpreter is allowed to decide what a sentence *probably means*. It is not allowed to decide what the farm data *is* or to execute an action.

## 1. Telemetry validation and identity

Incoming ESP32 telemetry is validated before storage. Sensor identity and active paddock membership are application/database concerns. MariaDB constraints provide another validation boundary.

FarmPi stores and distinguishes device observation time and FarmPi receipt time. The language model does not participate in clock synchronisation, sensor identity, deduplication, SQL or measurement validation.

## 2. Speech/domain normalisation

Android/device speech recognition can provide several transcript alternatives. `app/speech_normalizer.py` uses transparent FarmPi vocabulary cues and current paddock names to prefer a better alternative when there is strong domain evidence.

Known contextual transcription errors currently include forms such as `Patek` and `padlock` for `paddock`. Corrections only occur when farming/measurement context exists, so an unrelated sentence about a padlock or a Patek watch is left unchanged.

When normalisation changes a transcript, the client can show both **Heard** and **Interpreted** text. This keeps speech-recognition errors visible during learner evaluation.

## 3. Fast deterministic router

`app/question_router.py` remains useful for obvious requests such as a clearly phrased current measurement, average, ranking, comparison, history or paddock inventory question.

It is now an **optimisation**, not the definition of valid learner language.

A learner does not need to know the exact syntax accepted by a regex. If wording is ambiguous, colloquial, indirect, source-oriented or action-like, FarmPi can invoke the semantic interpretation layer instead.

## 4. Semantic learner-intent interpretation

`app/semantic_interpreter.py` asks the configured language model to convert natural language into a small JSON contract. Example:

```json
{
  "intent": "rename",
  "confidence": 0.96,
  "paddock_name": "Paddock A",
  "new_paddock_name": "North Flat",
  "measurement": null,
  "operation": null
}
```

or:

```json
{
  "intent": "learning",
  "confidence": 0.98,
  "topic": "milk fever in dairy cows"
}
```

The interpreter prompt explicitly expects ordinary, polite, colloquial, regional, accented/transcribed and incomplete English. Its output is validated by Python before being mapped to a reviewed FarmPi route.

Low-confidence action interpretations do not execute. FarmPi asks the learner to clarify.

Every rename-looking phrase is semantically interpreted before the mutation path. This prevents conversational words such as a trailing `please` from accidentally becoming part of a new paddock name while still allowing a learner to explicitly choose a name that genuinely contains such a word.

## 5. Deterministic paddock identity

Paddock references are resolved against FarmPi state, not model memory. The resolver supports current names, audited previous names and configured letter/numeric aliases.

The semantic model may suggest that `field B` means `Paddock B`; the deterministic resolver still decides whether that paddock actually exists and which stable database ID it represents.

This separation preserves history when a display name changes.

## 6. Deterministic farm data and calculations

`app/farm_data.py`, `app/analytics.py` and the measurement catalogue remain factual authority for FarmPi telemetry.

The language model does not calculate sensor-derived values. Reviewed deterministic operations include current readings and supported:

- farm-wide averages;
- highest/lowest rankings;
- comparisons;
- minimum/maximum/average over bounded history where supported;
- change and trends where supported;
- rainfall totals;
- range/anomaly operations where defined by the catalogue;
- graph/evidence payloads.

For example, if FarmPi supplies:

```text
Farm average air temperature across 16 active paddocks: 17.42 °C.
```

that figure was produced by application code over the validated FarmPi snapshot. The LLM may explain it but does not recalculate it.

## 7. Mutation boundary

A semantic interpretation can identify a requested action, but it cannot execute it.

Paddock rename remains:

```text
learner language
    ↓
semantic rename intent
    ↓
deterministic paddock resolution
    ↓
new-name validation
    ↓
short-lived confirmation token
    ↓
explicit learner confirmation
    ↓
application/database update + audit
```

Qwen neither authorises nor performs the database mutation.

The same principle should apply to future state-changing FarmPi operations.

## 8. Agricultural learning is intentionally broader

General agricultural questions are not required to map to a FarmPi database operation.

FarmPi can teach about cows, sheep, pasture, soils, irrigation, weather, effluent, animal health and related practical agriculture. General model knowledge is allowed for explanation, subject to one important boundary: **general agricultural knowledge is not evidence about this particular farm and is not automatically an official New Zealand recommendation**.

A question such as `Why do cows get milk fever?` can therefore be answered as a learning question. A question such as `Why did this cow get milk fever?` must not be presented as a verified diagnosis merely because the model can explain general causes.

## 9. Curated authoritative sources

`app/knowledge_sources.py` contains the first source registry for trusted New Zealand agricultural material. Initial organisations include:

- DairyNZ;
- Ministry for Primary Industries (MPI);
- Earth Sciences New Zealand;
- Irrigation New Zealand.

The registry can provide source metadata and reviewed claims to the teaching model. FarmPi may attribute those supplied claims to the named source.

The current prototype does **not yet contain a general live web-search/retrieval provider**. It must therefore not say `I searched DairyNZ` merely because a DairyNZ source reference was included. A provenance entry explicitly records when a research request was answered from the curated source directory rather than live retrieval.

A later external-research provider can add a separate `retrieved/researched` provenance class once FarmPi really performs retrieval.

## 10. Provenance classes

FarmPi's API distinguishes the origin of information rather than pretending all statements have the same authority.

Current classes are:

- **observational** — validated FarmPi telemetry/database facts;
- **calculated** — deterministic FarmPi analytics over observations;
- **educational** — version-controlled FarmPi learning material;
- **authoritative** — curated authoritative external source material;
- **researched** — reserved for material actually retrieved by an external-research provider;
- **general** — model explanatory knowledge, not a farm observation or official source;
- **combined** — a response that intentionally uses more than one class.

The response also carries a `provenance` list. Android exposes it with evidence under **Show sources / evidence**.

## 11. Prompt boundary

`app/app.py` tells the answering model to:

- converse naturally and teach concisely;
- treat FarmPi verified facts as authoritative for this farm;
- treat deterministic calculations as authoritative calculations;
- attribute curated source claims only when supplied;
- never claim live research unless retrieval actually happened;
- use general agricultural knowledge for teaching without converting it into a farm-specific fact;
- avoid unsupported farm-specific diagnoses or operational decisions;
- explain uncertainty and offer one useful next learning direction.

This is intentionally less restrictive than the older `use only verified facts` prompt because that old contract prevented useful education. The strong controls now sit where they belong: around facts, calculations and actions.

## 12. Model role

The current reference development model is Qwen3.5-9B hosted by LM Studio on the development PC. It is used in non-thinking mode so short FarmPi interactions are not consumed by hidden reasoning tokens.

The model performs two distinct language functions:

1. semantic interpretation for wording that the fast route should not be expected to enumerate;
2. concise educational rendering/explanation.

Neither function gives it direct SQL or mutation authority.

## 13. Behavioural tests

The test suite now covers both deterministic authority and language variation. Relevant files include:

- `tests/test_question_router.py`;
- `tests/test_conversational_paddocks.py`;
- `tests/test_conversational_architecture.py`;
- `tests/test_conversational_variation.py`;
- `tests/test_semantic_interpreter.py`;
- `tests/test_speech_normalizer.py`;
- `tests/test_farm_data.py`.

Language tests deliberately include polite, indirect and colloquial variants rather than only one canonical phrase. The objective is not to enumerate every possible sentence; it is to preserve the semantic/deterministic boundary while demonstrating that different natural phrasings can reach the same controlled operation.

The Pi `./update` process runs the Python validation/tests before service restart, so a failed routing/control regression stops deployment.

## Design rule going forward

When deciding whether to add a new guardrail, ask:

> **Does this protect a farm fact, calculation, identity, external-source claim or state-changing action?**

If yes, deterministic control or explicit provenance is appropriate.

If the proposed guardrail merely forces a learner to phrase a valid agricultural question in one particular way, it is probably in the wrong layer.
