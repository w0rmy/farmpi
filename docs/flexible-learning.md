# FarmPi flexible-learning architecture

## Purpose

FarmPi is a **conversational agricultural learning system** built on top of monitored farm data. The intended learner experience is closer to an ordinary conversation with a capable teaching assistant than to a natural-language command interface.

This is a central implementation of the **Developing Flexible IT Courses** elective within the capstone. The learner should be able to use their own language, ask follow-up questions, change direction, ask for simpler or deeper explanations, and explore related farming topics without first learning FarmPi's command grammar.

FarmPi remains focused on practical New Zealand agriculture, with dairy farming and the FarmPi sensor platform as its strongest initial context. Legitimate learning topics include cows, sheep, pasture, soils, irrigation, weather, effluent, animal health, farm systems and related agricultural practice.

## Architectural turning point — 27 August 2026

Early FarmPi development deliberately emphasised grounding, deterministic routing and deny-by-default guardrails. That architecture was effective at protecting sensor/database facts and state-changing actions, but testing exposed an important limitation: **the same restrictions that made the data interface reliable also made the learning interface brittle**.

Examples included natural requests such as `Can you rename Paddock A to Paddock 1?` falling outside an exact rename grammar, broad capability questions being mistaken for paddock references, and ordinary explanatory questions being routed to `unsupported`, `causal-boundary` or other refusal-style responses.

The conclusion is not that grounding was a mistake. The boundary was simply drawn too broadly. FarmPi should tightly control **what it claims about this farm and what it is allowed to change**, but it should not tightly control **how a learner is allowed to speak or what related agricultural concept they are allowed to explore**.

The revised design principle is:

> **Actions and farm-specific factual claims remain controlled and deterministic; conversation, explanation, exploration, paraphrase tolerance and agricultural learning become substantially more open.**

## Target interaction architecture

```text
Natural learner conversation
        ↓
Speech/domain normalisation when needed
        ↓
Semantic learner-intent interpretation
        ↓
Choose relevant knowledge / tools
        ├── FarmPi validated sensor/database facts
        ├── deterministic calculations and analytics
        ├── curated authoritative NZ agricultural sources
        ├── external research when a retrieval provider is available
        └── general agricultural explanatory knowledge
        ↓
Deterministic execution boundary for facts/actions
        ↓
Combine information with explicit provenance and uncertainty
        ↓
Concise teaching response
        ↓
One useful next learning direction
```

The semantic interpreter is therefore **not an execution agent**. It may interpret `Could you please call field A North Flat?` as a rename request, but the existing paddock resolver, validation, confirmation token and database mutation code still perform the action. Likewise, it may interpret `Which field is looking driest?`, but Python selects the verified measurement and calculates the ranking.

This separation allows language to be flexible without making factual authority flexible.

## Fast routes are an optimisation, not the language contract

The deterministic regex router remains useful for unambiguous common operations. It is now treated as a **fast path**, not as a complete definition of valid learner English.

Ambiguous, colloquial, indirect or source-oriented wording can pass through `app/semantic_interpreter.py`, which asks the configured reference model for a small structured interpretation such as:

```json
{
  "intent": "current",
  "confidence": 0.93,
  "paddock_name": "Paddock B",
  "measurement": "air_temperature_c"
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

The application validates the structured result and maps it to an existing controlled operation or learning path. Low-confidence action interpretations ask the learner to clarify rather than guessing.

All rename-looking language is semantically interpreted before execution. This is particularly important for polite language: `Rename Paddock A to North Flat please` must not accidentally create a paddock literally named `North Flat please` merely because an old regular expression consumed the entire suffix.

## Open agricultural learning

FarmPi no longer treats the absence of a database operation as a reason to reject an agricultural question. Examples that should be normal learning interactions include:

- `Why do cows get milk fever?`
- `What does a high somatic cell count mean?`
- `Why can pugging damage pasture?`
- `What is pasture residual?`
- `How does effluent irrigation work?`
- `What causes facial eczema in sheep?`
- `Why does soil pH matter?`
- `What does DairyNZ say about irrigation scheduling?`
- `Can you explain refill point more simply?`
- `I didn't understand that — can you explain it another way?`

For general agricultural education the language model may use general knowledge to explain a concept. It must not silently turn general knowledge into a claim about the learner's farm or into an official New Zealand recommendation.

A FarmPi answer may therefore combine different kinds of knowledge, for example:

> `Paddock 4's current soil moisture is 17%. That value comes from FarmPi's validated telemetry. DairyNZ's reviewed irrigation guidance considers soil moisture relative to refill point and field capacity along with rainfall, evapotranspiration and irrigation capacity. FarmPi does not have enough farm-specific information to decide whether irrigation is required. Would you like me to explain refill point?`

This is preferable to a generic refusal because it teaches while preserving the evidence boundary.

## Provenance classes

FarmPi now models provenance explicitly. The main information classes are:

1. **FarmPi observation** — validated sensor/database values for this farm.
2. **Deterministic calculation** — averages, rankings, trends and other reviewed calculations produced by FarmPi application code.
3. **Curated authoritative source** — reviewed material or source metadata from organisations such as DairyNZ, MPI, Earth Sciences New Zealand and Irrigation New Zealand.
4. **Retrieved/researched source** — information obtained by a future live external-retrieval provider. This class must not be claimed unless retrieval actually occurred.
5. **General explanatory knowledge** — agricultural explanation from the language model, explicitly not a verified observation about this farm or an official recommendation.

The Android client exposes this information under **Show sources / evidence**. The goal is not to burden every short answer with bureaucratic labels; it is to make the origin of important claims inspectable when the learner wants to see it.

## Current NZ source directory

`app/knowledge_sources.py` contains the first reviewed source registry. Initial sources include:

- DairyNZ irrigation scheduling;
- DairyNZ general farming information;
- Ministry for Primary Industries animal-welfare codes;
- MPI sheep and beef cattle welfare material;
- Earth Sciences New Zealand data and applications;
- Irrigation New Zealand soil-moisture monitoring material.

The registry contains source metadata and a small number of reviewed claims. **It is not yet a live web-search service.** FarmPi is explicitly instructed not to say that it searched a source live unless a retrieval provider actually performed that search. Adding controlled live research is a subsequent integration stage.

## Speech and language variation

Speech recognition remains device-side and Android requests multiple recognition alternatives. `app/speech_normalizer.py` uses FarmPi vocabulary and known paddock names to prefer a more plausible alternative where there is strong domain evidence.

Observed transcription variants such as `Patek` and `padlock` can be corrected to `paddock` only when farming context exists. Unrelated language such as `the padlock is broken` is left untouched.

After speech normalisation, the same semantic interpretation layer used for typed input handles variation in sentence shape. This is important because Flexible Learning cannot assume one accent, dialect, cultural style or level of technical vocabulary. FarmPi should tolerate examples such as:

- `Could I have the temperature for field B please?`
- `Give us the temp for B.`
- `What's B looking like temperature-wise?`
- `How warm is number two at the moment?`
- `Which field is looking the driest?`
- `Please can you change field A's name?`

The design does not attempt to encode cultural stereotypes. Instead, testing deliberately varies politeness, directness, colloquial phrasing, sentence completeness, aliases and speech-recognition errors.

## Conversation and execution remain separate

The open learning architecture does **not** weaken the following controls:

- sensor/database values are never invented;
- paddock identity is resolved against configured FarmPi state;
- SQL remains application-controlled;
- deterministic analytics remain application calculations;
- database writes and renames remain explicit application operations;
- renames still require confirmation;
- model-generated interpretation cannot directly call SQL or mutate state;
- uncertainty about a farm-specific diagnosis or operational decision must be stated rather than hidden.

The model has more freedom to understand and teach, not more authority to alter the farm system.

## Learner preferences

The Android client maintains local explanation-depth (`simple`, `normal`, `technical`) and guidance-frequency (`more`, `normal`, `less`) preferences. These alter presentation and learning support, not the underlying farm facts.

Normal answers remain intentionally concise. If a learner wants more, they can ask a follow-up. This keeps the interaction approachable and also reduces inference latency.

Current answer ceilings are:

- Simple: 64 tokens;
- Normal: 96 tokens;
- Technical: 128 tokens.

These are safety ceilings rather than target lengths. The system prompt still asks for one to three short sentences and at most one useful follow-up question unless the learner asks for depth.

## Android learner experience

The native Android client supports:

- typed and spoken questions;
- multiple speech-recognition alternatives;
- visible **Heard** / **Interpreted** text when normalisation changes speech;
- text-to-speech answers;
- a prominent Speak button that changes to **Stop** while FarmPi is speaking;
- answer and suggested next learning steps before preference controls;
- charts and evidence for deterministic analytics;
- provenance/source inspection;
- Simple/Normal/Technical explanation depth;
- More/Normal/Less guidance frequency;
- short teach-by-doing activities in the Learn area.

Backend application errors are now distinguished from transport/TLS failures. If FarmPi returns a specific HTTP error such as an unavailable language model, Android displays that backend detail rather than always telling the learner to check certificate trust.

## Evaluation

Flexible Learning evaluation should test whether FarmPi adapts to people rather than whether people learn the correct FarmPi syntax. Useful test dimensions include:

- direct versus polite requests;
- colloquial and incomplete wording;
- different speakers and accents;
- speech-recognition alternatives and common transcription errors;
- novice versus technical explanations;
- follow-up questions and topic changes;
- broad agricultural learning questions;
- source-oriented questions such as `What does DairyNZ say ...?`;
- clear separation between a verified FarmPi observation and general agricultural knowledge;
- recovery when interpretation confidence is low;
- whether the suggested next question actually helps learning continue.

The capstone evidence should record both successful interactions and failures that cause the architecture to be refined. The 27 August 2026 move from regex/guardrail-first interaction to semantic learner-intent interpretation is itself an important example of evaluation driving redesign.
