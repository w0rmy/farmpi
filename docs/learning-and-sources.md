# AI, grounding, and source integration

## Current role

FarmPi combines deterministic application logic with a language model. The purpose of this layer is functional: let a user ask ordinary questions, interpret imperfect wording, explain available information, and connect natural-language requests to verified application capabilities without giving the model authority over farm facts or database operations.

This document previously described the project primarily as an embedded learning platform. That direction was superseded on 2 September 2026 when the capstone elective changed from **Developing Flexible IT Courses** to **Advanced Application Development Concepts**. The earlier learning work remains recorded in [course-design.md](course-design.md) and the [development record](development-record.md).

## Hybrid application boundary

FarmPi separates responsibilities deliberately:

1. **Deterministic application layer** owns sensor data, paddock identity, database access, calculations, chart values, timestamps, confirmations, mutations, and capability metadata.
2. **Semantic interpretation layer** maps varied natural language into a small validated intent schema when the fast router is insufficient.
3. **Language-model layer** explains, paraphrases, converses, and answers broader informational questions using supplied context and clearly scoped model knowledge.
4. **Source/provenance layer** records where supporting information came from and prevents a source directory or model assertion from being presented as verified farm evidence.

The model never selects arbitrary SQL and never receives authority to create farm measurements, calculate hidden chart values, rename a paddock, or bypass application validation.

## Natural-language interpretation

FarmPi uses two complementary routing layers:

- `app/question_router.py` handles clear reviewed farm-data and action patterns quickly.
- `app/semantic_interpreter.py` asks the configured model for a constrained JSON interpretation when wording is broad, indirect, conversational, source-oriented, or otherwise ambiguous.

The returned interpretation is validated before it can become an application route. Confidence, measurement, paddock, operation, window, topic, and proposed names are checked by application code.

A short-lived bounded conversation context allows follow-ups such as `What about Paddock 2?` without granting unrestricted memory or execution authority.

Spoken input can pass through deterministic normalisation before routing. The Android client shows both Heard and Interpreted text when FarmPi changes the transcription.

## Capability recovery

A failed literal interpretation should not immediately become a generic model refusal. When possible, FarmPi should inspect its own capabilities and give the user the nearest useful result.

The intended recovery order is:

1. try the normal deterministic route;
2. use semantic interpretation when the wording is unclear;
3. inspect available measurements, analytics, graph types, sources, and supported operations;
4. map close concepts onto known capabilities when defensible, such as `sunlight` to light/lux;
5. offer the nearest valid alternative if the exact request cannot be completed;
6. ask for clarification only when a decision or identity genuinely cannot be resolved safely;
7. return a concise limitation only after useful recovery options have been exhausted.

For example, a request for an unsupported graph should not produce `I cannot make graphs`. The application should first determine whether it has a relevant measurement or related graphable series and, if not, state what comparable data it can show.

This is an application-usability and resilience requirement rather than a pedagogical rule.

## Evidence hierarchy

FarmPi prefers the highest relevant available evidence:

1. **First-class trusted evidence:** deterministic FarmPi data, DairyNZ, and relevant New Zealand government sources where actual reviewed/retrieved material is available.
2. **Trusted primary sources:** organisations speaking authoritatively about themselves, their products, or their own specifications.
3. **Reputable general sources:** universities, research institutes, standards bodies, and established technical or industry sources.
4. **General or unverified web material:** useful only with suitable qualification and never proof of a FarmPi fact.
5. **Model knowledge:** a concise general explanation when no stronger evidence is available, labelled as model/general knowledge rather than farm evidence.

A source's presence in the catalogue does not itself prove a claim. Named-source attribution requires actual reviewed or retrieved supporting material.

## Current curated sources

`app/knowledge_sources.py` currently registers reviewed NZ source metadata for subjects including:

- DairyNZ irrigation scheduling and general farming information;
- Ministry for Primary Industries animal-welfare codes;
- the MPI Code of Welfare for Sheep and Beef Cattle;
- Earth Sciences New Zealand data and applications;
- Irrigation New Zealand soil-moisture monitoring.

The repository does not currently include a general live web-search provider. Source-oriented answers must not imply that a site was searched live when only curated metadata or a reviewed claim was supplied.

## Provenance model

Responses distinguish between:

- farm observation;
- deterministic calculation;
- reviewed application content;
- curated authoritative source metadata or reviewed claim;
- configured-model general explanation;
- live research status if a future provider is added.

The response source category summarises the information mix, while the provenance array keeps components inspectable. The highest evidence tier present does not erase weaker supporting components.

## General information and farm-specific claims

FarmPi may answer safe and lawful informational questions even when they are not directly about the farm. Relevance changes depth and source priority, not permission to answer.

That openness does not allow external or model knowledge to become an unsupported claim about this farm. Current readings, historical values, comparisons, device state, paddock identity, calculations, and mutations remain application-controlled.

## Decision and causal boundaries

FarmPi may explain factors involved in a farm decision and show verified current data, but it should not silently turn incomplete data into a farm-specific forecast, diagnosis, causal conclusion, irrigation decision, or autonomous recommendation.

A time series can demonstrate association or sequence; it does not prove cause. The same boundary applies to animal-health and agronomic interpretations.

## Failure behaviour

- Missing deterministic data should report the actual unavailable evidence or dependency rather than inventing a value.
- A model outage should not break deterministic farm-data requests.
- Invalid state-changing language must never fail open into a mutation.
- Unknown or ambiguous paddocks should return useful active-name recovery guidance.
- Missing live research must not produce fabricated citations.
- User-facing errors should avoid internal implementation terms such as `deterministic operation`, route names, SQL, or model-server jargon unless diagnostic detail is explicitly requested.

## Evaluation focus

Current evaluation should test whether the AI/data integration improves the functional application without compromising deterministic authority:

- Can ordinary and imperfectly worded requests reach the correct capability?
- Are farm values identical regardless of phrasing or model output?
- Do generic graph requests resolve to farm-wide data where appropriate rather than inventing a paddock?
- Can unsupported requests recover to a useful nearby capability?
- Are source and provenance claims accurate?
- Does the model remain useful when it cannot directly satisfy the literal request?
- Can a model or database outage fail clearly without corrupting the rest of the application?
