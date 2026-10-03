# Capstone acceptance consolidation — 3 October 2026

## Purpose

This record consolidates the current FarmPi capstone acceptance state before the repository is frozen as the stakeholder-test baseline.

The pre-documentation code baseline is:

- repository: `w0rmy/farmpi`
- branch: `main`
- revision: `1e787d8bfab9d7db5fef82a13bca7a653aa2bcad`
- latest reported Raspberry Pi regression result after PR #48: **192 tests, OK**

This consolidation does not reinterpret simulation as physical evidence and does not replace the separate stakeholder/usability evaluation.

## Current acceptance state

| Check | Current state | Basis / boundary |
|---|---|---|
| T01 — Physical sensing | **PARTIAL (1/6)** | XC4604 soil moisture is accepted end to end on FP-001 / HW 33C0. Soil temperature, air temperature, relative humidity, light and barometric pressure remain physically undemonstrated. |
| T02 — Communication and freshness | **PASS** | Project-owner/operator confirmation that the previously completed communication/freshness acceptance passed. This consolidation records the closure state; it does not reconstruct a missing raw transcript. |
| T03 — History and storage | **PASS** | Project-owner/operator confirmation that the previously completed history/storage acceptance passed. This consolidation records the closure state; it does not invent additional raw measurements or logs. |
| T04 — Thresholds and alerts | **DEFERRED / NOT A CURRENT ACCEPTANCE CHECK** | FR06/FR07/T04 are deliberately deferred to a future release under the current capstone requirements baseline. This is scope control, not a failed test. |
| T05 — Analysis and AI grounding | **PASS / CLOSED** | Live authority-boundary acceptance plus the retained T05 record, PR #47 known-value fixture strengthening, PR #48 stale-test correction, and the clean 192-test regression result. |
| T06 — Offline use and startup | **PASS — developer/operator acceptance** | Local/offline operation, network loss/reconnection, System Status, voice/TTS and managed-node administration were accepted during developer/operator testing. This does not complete comparative human usability evidence. |
| T07 — Maintainability and repeatability | **PASS** | A new Raspberry Pi SD card was installed and FarmPi was successfully reinstalled using the documented deployment approach. This is direct repeatability evidence rather than an assumption based on documentation alone. |

## T05 closure addendum

The original 2 October T05 record was deliberately left at **STRONG PARTIAL** because two closure items were still weak.

Both were subsequently closed:

1. **Deployment-specific invalid action:** a request to rename a paddock to its existing current name was rejected deterministically with:
   `New paddock's name is already its current name.`
   FarmPi did not offer confirmation and did not mutate accepted state.

2. **Known-value comparison evidence:** PR #47 strengthened the deterministic comparison fixture so expected and actual values were explicitly linked.

The following regression run then exposed one stale wording assertion rather than an application defect. The test expected `Highest average Soil moisture over` while the correct application response used `Highest average soil moisture over`. PR #48 corrected the test expectation without changing the application behaviour. The subsequent Raspberry Pi suite was reported clean at 192 tests.

T05 is therefore **PASS / CLOSED** for the current demonstrator baseline.

## Stakeholder/usability evidence remains open

Developer/operator acceptance is not a substitute for the human stakeholder evidence required by the capstone.

The planned participant session now uses the FarmPi Stakeholder Presentation Pack as the **minimum standard onboarding** before the practical test. The session then measures three separate things:

1. **onboarding sufficiency** — whether the short presentation is enough to prepare the participant;
2. **knowledge transfer** — whether the participant can carry the concepts from the presentation into the live phone interface even where the screens are not identical;
3. **post-onboarding usability** — whether the participant can complete realistic FarmPi tasks without further coaching.

Additional help may be given if the participant becomes genuinely stuck, but the assistance must be recorded.

The remaining human evidence is therefore still open:

- E6-09 — stakeholder conversation / observation;
- E6-10 — feedback that validates or changes the design;
- E6-11 — comparative fixed-interface versus Ask FarmPi usability evidence.

## Release-baseline rule

After this documentation-only reconciliation is merged, the resulting `main` is intended to be frozen as the **stakeholder-test / capstone baseline**.

No further feature work is planned unless:

- stakeholder testing exposes a material usability defect worth correcting;
- one of the remaining five T01 physical channels requires a necessary integration correction; or
- a genuine evidence/requirements contradiction is discovered.

A stakeholder-driven change is not a failure of the freeze. It is new capstone evidence and must be recorded as such.
