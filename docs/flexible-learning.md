# FarmPi flexible-learning scaffold

## Purpose

FarmPi is beginning to move from a passive question-and-answer interface toward a guided learning interface. This is the first implementation step for the **Developing Flexible IT Courses** elective within the capstone.

The aim is not to turn FarmPi into an unrestricted chatbot. The user experience can become more helpful, conversational, and adaptive while factual authority and state-changing actions remain deterministic.

## Controlled conversational learning

The first router pass was too deny-by-default for learner language: it attempted to force ordinary phrasing into a small regex catalogue, which produced brittle interactions and misleading paddock errors. FarmPi now grounds **farm facts and actions**, not every possible sentence. Capability and approved topic questions receive curated material; otherwise ordinary learning prompts can reach Qwen with a controlled learning context. Qwen can clarify, summarise, and teach, but cannot invent a measurement, resolve a paddock, calculate an analytic, make a farm decision, or change state.

This means `What sort of other information can you show me?` gets a capability overview, and `Should I irrigate Paddock A?` becomes a short teaching exercise: FarmPi states the decision boundary, includes a verified moisture value when one exists, explains relevant approved factors, and offers a next concept to learn. It never gives an irrigation recommendation.

## Current guided interaction

The browser interface now provides:

- a short onboarding introduction;
- initial example questions;
- a **Guide me** button;
- browser speech input and text-to-speech output;
- context-sensitive suggested follow-up questions after each answer.

The initial guidance is supplied by `app/guidance.py` rather than generated from model memory.

When the user taps **Guide me**, FarmPi asks the local LLM to explain how to use the system. That request still passes through the normal deterministic routing and grounding path. Qwen receives verified capability facts describing what FarmPi can and cannot currently do.

## Why the guidance is deterministic

The interface should not teach the user capabilities that the application does not actually possess. For that reason:

```text
known FarmPi capabilities
        ↓
app/guidance.py
        ↓
help route
        ↓
VERIFIED FACTS
        ↓
Qwen
        ↓
natural-language explanation
```

Likewise, suggested next questions are selected by application logic. They can direct the user toward temperature, humidity, moisture, pH, light, and supported moisture calculations without prompting unsupported farm recommendations.

## Current examples

A new user can be prompted with questions such as:

- `Which paddock is driest?`
- `What is Paddock A's air temperature?`
- `What is Paddock A's relative humidity?`
- `How many paddocks are we monitoring?`
- `What stats are available on Paddock B?`
- `What is the temperature in Paddock 2?`
- `How do I use FarmPi?`

The expanded synthetic-farm stage adds grounded examples such as:

- `Which paddock is tallest?`
- `What is the soil EC in Paddock C?`
- `How much rainfall was there over the last 24 hours?`
- `What is the pasture height change in North Flat over the last day?`
- `Rename Paddock A to North Flat`

After a user asks about one paddock, FarmPi can suggest other supported measurements for the same paddock. It also retains a small, explicit conversation token for 30 minutes: after a current measurement question, `What about Paddock 2?` reuses that supported measurement for the second configured paddock. Numeric aliases follow the active database paddock order and keep the same identity after a paddock is renamed. This gives the interaction continuity without requiring the user to know the system's exact vocabulary in advance.

## Speech

The existing browser text-to-speech option remains enabled by default. A normal FarmPi answer, including the response to **Guide me**, can therefore be spoken on the user's phone or browser device.

Speech recognition remains browser/device-side. The browser requests up to five final alternatives in `en-NZ`, including the confidence value when the browser exposes one. FarmPi does not replace that service with a cloud recogniser or ask Qwen to guess what was said.

Instead, spoken input follows this deterministic path:

```text
browser STT
        ↓
app/speech_normalizer.py
        ↓
deterministic router/action layer
        ↓
grounding and approved database operation
        ↓
Qwen language response
```

The normaliser uses aliases from the central measurement catalogue and the active MariaDB paddock display names as a small farm vocabulary. It can prefer a clearly better browser alternative and applies a short, contextual list of known corrections. The initial real usability finding is `Patek` being transcribed for `paddock`; for example, “What is the moisture in Patek C?” becomes “What is the moisture in Paddock C?” Browser phrase/context biasing is inconsistent across browsers, so this reviewed deterministic layer is the reliable FarmPi behaviour.

When a paddock phrase cannot be resolved, FarmPi distinguishes interpretation from data availability. It may safely resolve one very close name, ask `Did you mean ...?` for a medium-confidence candidate, or list valid active paddocks and an example question when confidence is low. This is deliberate Flexible Learning behaviour: recovery teaches the language that works instead of implying that telemetry does not exist.

Corrections are deliberately cautious. A sentence about a Patek watch is not changed, and an ambiguous alternative keeps the browser's top transcript. When a correction or alternative selection occurs, the UI displays **Heard** and **Interpreted** text. That makes evaluation practical: a tester can identify whether an error originated in speech recognition or FarmPi's interpretation. Typed input bypasses the normaliser unchanged.

Speech-normalised rename requests still only create a five-minute confirmation proposal. They cannot bypass the existing explicit confirmation or mutate MariaDB directly.

## Scope of the first stage

This stage is deliberately modest. It demonstrates:

- onboarding;
- repeated contextual guidance;
- natural-language help;
- example prompts;
- spoken responses;
- separation of learning guidance from factual authority.

The native Android milestone now keeps a local explanation-depth (`simple`/`normal`/`technical`) and guidance-frequency (`more`/`normal`/`less`) preference and sends it with a request. FarmPi changes only phrasing/token budget and the number of deterministic suggestions; it never changes verified facts or allowed operations. Its Learn tab starts with short teach-by-doing tasks rather than static training material. It does not yet implement a persistent learner profile.

## Planned adaptive-learning layer

The next useful stage is a small persistent user interaction profile. Candidate preferences include:

- explanation depth: simple / normal / technical;
- answer length;
- preference for plain language, table, graph, or raw values;
- how frequently FarmPi offers guidance;
- whether onboarding/help should be repeated;
- whether spoken responses are preferred.

Explanation depth (simple / normal / technical) and guidance frequency (more / normal / less) are deliberately the immediate next stage, rather than rushed into the 16-paddock implementation. They must alter explanation and prompting only, never the verified facts or the allowed operations.

The important architectural rule is that these preferences change **how verified information is explained**, not which facts are true.

A future interaction path can therefore become:

```text
User question
      +
User learning/preferences profile
      ↓
Deterministic FarmPi result
      ↓
Grounding/control layer
      ↓
Qwen
      ↓
Answer adapted to that user
```

## Evaluation

The flexible-learning component should eventually be evaluated with a nontechnical user. Useful observations include:

- whether the onboarding explains what can be asked;
- whether suggested questions help the user continue without instruction;
- whether simple versus technical explanations are understandable;
- whether speech improves accessibility or convenience;
- where users become confused about what FarmPi can and cannot know.

These observations can then drive a second iteration of the interface and provide direct capstone evidence of evaluation and refinement.
# Current implementation note

The initial scaffold is now backed by version-controlled educational concepts, distinct Simple/Normal/Technical materials, More/Normal/Less suggestion counts, real-action learning activities, and Android-local learner preferences. See [educational grounding](educational-grounding.md) and [the visual learning flow](diagrams/flexible-learning.mmd). It remains deliberately lightweight: no account system, gradebook, or full LMS.
