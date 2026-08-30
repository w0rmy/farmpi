# Learning design, grounding, and sources

## Educational purpose

FarmPi should teach through ordinary use. A learner can ask naturally, inspect a result, request another explanation level, view evidence or sources, and follow a suggested next question without first learning a command grammar, database vocabulary, sensor conventions, or prompting technique.

The monitoring system is the vehicle. Developing Flexible IT Courses is evidenced through onboarding, voice/text access, explanation adaptation, teach-by-doing activities, evidence navigation, visual presentation choices, recovery guidance, and user evaluation. AI and Data Sciences is evidenced through structured interpretation, deterministic retrieval/analytics, provenance, constrained model use, source selection, and measured model/deployment trade-offs.

## Open conversation with controlled claims

Relevance determines evidence quality and answer depth, not permission to answer. A learner may ask about dairy farming, livestock, soils, pasture, irrigation, weather, effluent, animal health, farm systems, or an apparently unrelated subject they consider useful. FarmPi should give a short helpful answer with appropriate uncertainty.

This openness does not extend to farm facts or actions. Readings, history, timestamps, comparisons, device state, paddock identity, calculations, and mutations remain application-controlled and are never invented. General or external knowledge must not be converted into a statement about this farm.

## Routing and interpretation

FarmPi uses two complementary layers:

1. `app/question_router.py` recognises obvious reviewed farm-data and action shapes quickly.
2. `app/semantic_interpreter.py` asks the configured model for a small JSON interpretation when language is broad, polite, indirect, source-oriented, or action-shaped. The parser validates intent, confidence, measurement, paddock, operation, window, direction, topic, and proposed name before application code maps it to a permitted route.

The semantic model does not select SQL or execute an action. Low-confidence or invalid action interpretation becomes a useful clarification. Non-action learning questions remain answerable even if interpretation is imperfect. A 30-minute opaque conversation token supports narrow contextual follow-ups such as `What about Paddock 2?`; it is not unrestricted model memory.

Spoken input has a deterministic normalisation pass before routing. It can select a clearly better browser alternative and correct known farm-context confusions such as `Patek`/`padlock` for `paddock`. The UI shows both Heard and Interpreted text when a change occurs.

## Evidence hierarchy

FarmPi prefers the highest relevant available evidence:

1. **First-class trusted evidence:** deterministic FarmPi data, Experience Edge, DairyNZ, and relevant `.govt.nz` sources. Prefer DairyNZ and relevant New Zealand government sources for New Zealand dairy/agricultural questions.
2. **Trusted primary sources:** organisations speaking authoritatively about themselves or their products, such as Fonterra on Fonterra or manufacturer documentation.
3. **Reputable general sources:** credible and relevant secondary material.
4. **General or unverified web:** useful only with clear qualification and never proof of a FarmPi fact or decision.
5. **Model knowledge:** a concise general explanation when no retrieved source is available, labelled as general knowledge rather than farm evidence.

First-class trusted is an evidential preference, not a blanket claim that every statement is infallible. A source can be inherently authoritative for its own current content - current legislation text, for example - while other claims still require relevance and context.

## Current curated sources

`app/knowledge_sources.py` currently registers reviewed NZ source metadata for:

- DairyNZ irrigation scheduling and general farming information;
- Ministry for Primary Industries animal-welfare codes;
- the MPI Code of Welfare for Sheep and Beef Cattle;
- Earth Sciences New Zealand data and applications;
- Irrigation New Zealand soil-moisture monitoring.

Only stored reviewed claims may be attributed as support. A registered source without a reviewed claim is a reference suggestion, not evidence for the generated statement. Experience Edge is included in the first-class policy but does not yet have a repository source record because no reviewed URL/claim package has been added.

FarmPi has no general live web-search provider in the current repository. Source-oriented requests therefore expose a `curated-source-directory-only` research status and must not say that the web or a named site was searched live.

## Provenance model

Responses separate:

- farm observation;
- deterministic calculation;
- reviewed FarmPi learning material;
- curated authoritative source metadata or reviewed claim;
- configured-model general explanation;
- live research status when a future provider is implemented.

The response's source category summarises the mix (`observational`, `calculated`, `educational`, `authoritative`, `researched`, `general`, or `combined`). `source_tier` uses one of the five hierarchy levels and reports the highest evidential tier present; `combined` remains a category rather than becoming a sixth tier. The provenance array keeps every component inspectable, including whether a named source supplied a reviewed claim or only a reference suggestion.

## Adaptation and teach-by-doing

Simple, Normal, and Technical change instructional depth, not the underlying fact. More, Normal, and Less change the number of proactive suggestions. The Android app stores these choices locally.

`GET /api/learning/course` exposes the controlled course aim, four learning outcomes, five modules, reviewed Try prompts, success intents, lightweight self-checks, next-module references, and bounded response-intent mappings. It is source-controlled deterministic content, not an LLM-generated course. `GET /api/learning/activities` remains as a compatible concise activity catalogue.

The Android Learn tab presents the five modules as **Learn → Try → Ask → Check → Continue**. A Try becomes complete from a matching real returned intent where possible; a Check is learner reflection, not an assessment or grade. It stores only current/last module and completed Try/check/module markers in device-local preferences. Learners may follow the recommended sequence or open any module directly, and can return after a bounded ordinary `/api/ask` follow-up conversation.

Course-aware requests send a validated module id only. The backend supplies the corresponding reviewed context to model-assisted explanations and records it in provenance. It never treats Android text as system/course prompt material. Small course quick actions use the existing `conversation_id`; contextual Learn about this links use the reviewed response-intent mappings rather than cluttering every response with generic help.

The Android settings cog also offers six whole-app presentation themes and compact/standard/large text density. These support readability, contrast preference, cognitive comfort, and learner adaptation without changing content or facts. No custom artwork or animation workstream is intended.

## Decision and causal boundaries

FarmPi can teach the factors involved in an irrigation decision and can show a verified current reading. It cannot decide whether to irrigate because it does not store validated field capacity, refill point, forecast rainfall, evapotranspiration, soil type, restrictions, or system capacity.

Likewise, a sequence in telemetry may be described, but association is not proof of cause. FarmPi does not turn a chart into a diagnosis, forecast, animal-health conclusion, or farm-specific agronomic recommendation.

## Failure behaviour

- Deterministic farm requests report the specific unavailable dependency or missing evidence rather than guessing.
- A model outage on a learning route returns a limited useful response and preserves curated source/provenance status.
- Invalid action language returns clarification and never fails open into a mutation.
- Unknown or ambiguous paddocks provide active-name recovery guidance.
- Missing live research is disclosed; citations are never fabricated.

## Evaluation questions

The learning design should be tested with a non-technical user:

- Can they begin without formal training?
- Can they ask broad and imperfectly phrased questions?
- Can they distinguish observation, calculation, sourced guidance, and model knowledge?
- Can they use evidence/source disclosure without being overwhelmed?
- Do explanation depth, guidance level, theme, and text density improve comfort or task completion?
- Does the system recover constructively from speech or paddock-name errors?
- Do any controls or technical additions reduce learner agency or obscure the outcomes?
