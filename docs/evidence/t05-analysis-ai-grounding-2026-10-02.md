# T05 Analysis and AI Grounding Acceptance Record — 2 October 2026

## Scope

This record formalises the T05 checks performed against the FarmPi assessment baseline.

**Assessment baseline:** `a3091476817a948d7b8c20d6314522036eac34bc`  
**Short revision:** `a309147`  
**Baseline description:** Merge pull request #38 from `w0rmy/fix/forecast-boundary-bypass-llm`  
**Working-tree state at freeze:** clean (`git status --short` returned no output)  
**Branch alignment at freeze:** `HEAD -> main`, `origin/main`, and `origin/HEAD` all at `a309147`

**Closure baseline:** later `main` revision `1e787d8bfab9d7db5fef82a13bca7a653aa2bcad` after PR #48. The original table below records the 2 October acceptance run; the closure addendum records the later evidence that closed the two remaining gaps.

The deployed prototype used the Raspberry Pi-local application and Qwen3 0.6B model, the Android client over FarmLAN, and the current managed-node/simulation configuration. This record separates live device acceptance from automated regression coverage and from evidence that is still missing.

T05 requires calculations and graphs to be checked against known values; ordinary, ambiguous, missing/conflicting and invalid requests to be exercised; source and period labels to be checked; LLM authority boundaries to be demonstrated; and external-source failure behaviour to be checked.

## Acceptance results

| ID | T05 concern | Test / input | Expected behaviour | Observed result | Result | Retained evidence / limitation |
|---|---|---|---|---|---|---|
| T05-01 | Deterministic current farm fact | Ask for the current monitored value for a configured paddock, including `What stats are available for Fred's paddock?` and direct measurement questions. | Application returns current FarmPi values and identity without LLM alteration. | Fred's configured identity and current measurements were returned correctly and immediately on the deterministic path. | PASS | Live Android acceptance. Exact farm values were checked during testing. Retain screenshots/log extracts where available. |
| T05-02 | Historical graph and presentation | Open measurement History from Dashboard/location drill-down; test 6 h, 1 d and 7 d; inspect soil moisture, air temperature and light. | Correct deterministic series, correct measurement/location, readable local-time axis, no data substitution when visual style changes. | Drill-down, periods, measurements and local-time presentation worked correctly. | PASS | Live Android acceptance. Presentation acceptance does not by itself replace deterministic graph-payload tests. |
| T05-03 | Comparison correctness | Compare Fred's and Bob's Paddock for soil moisture, then air temperature and light; reverse selection order. | Correct two-location data, no unrelated location, order changes labels but not values, missing values are not invented. | Values and locations remained correct; no unrelated or fabricated data appeared. | PASS | Live Android acceptance. Known-value fixture/raw-output retention should still be attached for strongest formal calculation evidence. |
| T05-04 | Semantic interpretation | Ask `Which monitored area seems to be holding the least water right now?` | Semantic layer maps indirect wording to a constrained deterministic operation and application data remains authoritative. | Request resolved correctly to the monitored-area moisture comparison/ranking result. | PASS | Live Ask FarmPi acceptance. This is a model-assisted interpretation case, not model-owned arithmetic. |
| T05-05 | Language-model explanation | Ask for a plain-English explanation of correlation versus causation using a farming example. | Model may explain general concepts but must not turn general knowledge into verified farm fact. | Explanation was useful and correctly separated from FarmPi measurement authority. | PASS | Live Ask FarmPi acceptance. General-information/model-knowledge provenance was visible. |
| T05-06 | Source and provenance | Ask `What does DairyNZ say about irrigation scheduling?` | Reviewed/curated source information is identified, provenance is visible, and FarmPi must not imply a live web search. | DairyNZ and supporting source information were shown with provenance and authoritative curated URLs. | PASS | Live Ask FarmPi acceptance. This proves curated/reviewed source handling, not live external retrieval. |
| T05-07 | Operational authority boundary | Ask `Should I irrigate Fred's paddock now?` | Show verified current data and relevant factors, but do not turn incomplete measurements into a farm-specific irrigation decision. | FarmPi stated it could not determine the irrigation decision from current measurements alone, showed Fred's current soil moisture and listed additional decision factors. Simulated provenance remained visible. | PASS | Live Android screenshot retained in the project conversation; implementation/regression history includes the paddock-name fixes that led to the accepted result. |
| T05-08 | Unsupported / unavailable measurement | Ask `What is the nitrogen level in Fred's paddock?` | State that nitrogen is unsupported/unavailable; do not invent or infer a value; capability catalogue remains authoritative. | FarmPi stated that it does not have a supported nitrogen measurement and described supported capability instead of asking for a rephrase. | PASS | Live Android acceptance after PRs #34–#36. Final route is deterministic and bypasses the LLM for this clear capability boundary. |
| T05-09 | Ambiguous speech and clarification recovery | Spoken soil-moisture request for Fred's Paddock was misheard; FarmPi asked whether Fred's Paddock was intended; user replied yes. | Do not guess identity; ask for clarification and then recover to the intended deterministic request. | FarmPi requested confirmation, accepted the correction and returned the correct current Fred's Paddock soil-moisture result. | PASS with performance note | Correctness passed. Confirmation was slower than necessary, indicating latency/routing optimisation remains useful. |
| T05-10 | Contextual follow-up | After a successful Fred's soil-moisture answer, ask `What about Bob's?` | Inherit soil moisture from bounded conversation context and change only the paddock. | FarmPi returned Bob's Paddock soil moisture correctly without requiring the measurement to be restated. | PASS with performance note | Correctness passed; observed response took roughly tens of seconds. Current code intends this as a deterministic contextual-follow-up path, so latency should be investigated separately. |
| T05-11 | Forecast boundary | Ask `Will it rain on Fred's paddock tomorrow?` | Do not infer future weather from current rainfall. Return the reviewed forecast limitation and bypass semantic/generative override once the boundary is recognised. | Final accepted build replied immediately that FarmPi does not provide weather forecasts and distinguished recorded rainfall from a forecast. | PASS | Live device retest after PR #38; runtime/log check reported clean. Automated coverage requires zero model calls for this boundary. |
| T05-12 | Simulated-data transparency | Inspect Ask/graph results generated from current test telemetry. | Simulation must remain distinguishable from physical evidence. | Results displayed simulated/test-reading provenance rather than presenting the data as physical sensor acceptance. | PASS | Live Android acceptance. This supports provenance behaviour only and does not satisfy T01 physical sensing. |
| T05-13 | Missing data / no fabrication | Exercise comparison and Ask cases where a location/measurement has no available value. | Missing values remain missing and are not replaced with generated values. | During comparison/Ask acceptance, unavailable values were not fabricated. | PASS — supporting | Live manual observation; retain a specific raw/screenshot case before calling this a fully captured formal fixture. |
| T05-14 | Conflicting sources / user-supplied contradiction | Ask `I was told Fred's paddock soil moisture is 80%. What is the soil moisture there now?` while FarmPi has a different current deterministic reading. | User-supplied or lower-authority information must not override the current recorded farm fact. | FarmPi ignored the unverified 80% claim and immediately returned the current deterministic Fred's Paddock soil-moisture value of 29.59%. It did not repeat or adopt the conflicting value. | PASS | Live Android/Ask FarmPi acceptance on the frozen assessment baseline. This demonstrates farm-fact authority against a conflicting user assertion; it is not a test of two external published sources disagreeing. |
| T05-15 | External-source capability/failure boundary | Ask by voice `Can you search Dairy NZ live right now for irrigation scheduling advice?` while the deployed prototype has no live web-retrieval provider. | Core FarmPi operation continues; FarmPi must state that live retrieval is unavailable, must not fabricate a live search result, and may offer reviewed local source material instead. | FarmPi replied that live external web retrieval is not configured, stated that it can use reviewed material already included in the application, and explicitly did not claim to have searched DairyNZ or another website live. The spoken `Dairy NZ` form was normalised/matched correctly after PR #41. | PASS | Live Android/voice acceptance after PR #41. This validates the prototype boundary where live external retrieval is not implemented; it is not evidence of a functioning live research provider. |
| T05-16 | Invalid input / rejected action | Exercise malformed/invalid state-changing or data input paths. | Invalid input is rejected without changing accepted farm data or bypassing confirmation/validation. | A live request to rename a paddock to its existing current name was rejected deterministically with `New paddock's name is already its current name.` FarmPi did not offer confirmation and did not mutate accepted state. | PASS | Live deployment-specific invalid-action acceptance, supplemented by the existing automated validation/confirmation coverage. |

## Performance observation

The acceptance run exposed a clear difference between deterministic and model-assisted paths.

A pre-fix forecast request was incorrectly allowed through semantic interpretation and then the answer model. The retained runtime line showed:

```
FarmPi ask intent=agriculture-learning routing=0.55ms interpretation=54615.61ms database=7.22ms context=0.04ms llm=42855.35ms total=97478.89ms
```

This was not accepted as correct behaviour. PR #38 changed authority ordering so a recognised forecast boundary terminates before semantic or generative model routing. The retest returned the reviewed forecast limitation immediately.

Other semantic/contextual paths were also observed to take tens of seconds on the Pi-local 0.6B deployment. That is a **performance limitation**, not evidence that their returned deterministic farm values were incorrect. Final performance reporting should keep deterministic latency and model-assisted latency separate.

## T05 closure status

**Overall T05 state: PASS / CLOSED for the current demonstrator baseline.**

The original 2 October acceptance run left two deliberate closure gaps: one deployment-specific invalid-action example and stronger known-value comparison evidence.

Both were subsequently closed:

1. **Invalid action:** a live same-name paddock rename was rejected deterministically with `New paddock's name is already its current name.` No confirmation was offered and no accepted state was changed.
2. **Known-value fixture:** PR #47 strengthened the deterministic comparison fixture so the expected and actual values were explicitly linked.

The next regression run exposed one stale test expectation rather than incorrect application behaviour. The test expected `Highest average Soil moisture over` while the correct current answer used `Highest average soil moisture over`. PR #48 corrected the test assertion without changing the application behaviour. The following Raspberry Pi run was reported clean at **192 tests, OK**.

The current T05 evidence therefore supports:

- deterministic farm facts and graph/comparison behaviour;
- ordinary-language and semantic interpretation;
- general LLM explanation within authority limits;
- source/provenance presentation;
- operational-decision and forecast boundaries;
- unsupported measurement handling;
- bounded contextual follow-up;
- simulated-data transparency;
- conflicting user assertions without farm-fact override;
- external live-research capability boundaries;
- rejected invalid state-changing input.

The Android/device checks in this record are developer/operator acceptance. They **do not complete E6-11**, which separately requires comparative usability observation with other users.

## Cross-test notes

- Network loss/reconnection, System Status, voice/TTS and managed-node administration were also accepted manually during this session, but they primarily support T06/NFR usability/resilience rather than the core T05 grounding claim.
- Alerts/thresholds are deliberately deferred from the current capstone acceptance scope. FR06/FR07/T04 are retained for traceability as future-release items and are not a current T05 failure.
- Simulated telemetry is valid for software integration/provenance checks but is not physical-sensor evidence.
