# Testing, capstone evidence, and evaluation

The automated Python suite covers measurement ranges, telemetry clock semantics, sequence retry/idempotency, dynamic paddock names, speech normalisation, confirmation-only rename, existing deterministic grounding, and the repeatable database update contract. New analytics must be tested with controlled row fixtures for calculation, selected period, chart series, and evidence metadata; they must never require Qwen. The 27 August 2026 open-learning direction adds a separate test concern: source selection and provenance must be evaluated without weakening deterministic farm-fact or action boundaries.

Before a major feature is considered complete, update the affected text, Mermaid diagram source, tests, rationale, limitations, and user-facing instructions. Keep any rendered diagram export alongside its `.mmd` source when a formal document needs a portable image.

## Initial usability / learning test plan

Recruit a small number of nontechnical learners after deployment; do not fabricate results. Observe whether participants can understand simulated provenance, ask a one-paddock question, compare paddocks, interpret a graph/evidence panel, and recognise an unavailable farm-specific recommendation boundary. Also ask participants to pose broad agricultural questions in their own words, follow up naturally, and identify whether the response is a FarmPi observation, deterministic calculation, trusted guidance, research, or general explanation. Compare Simple and Technical explanations for clarity, note SpeechRecognizer mishearings and normaliser corrections, and ask whether More/Normal/Less guidance feels excessive or insufficient. Record task completion, confusion points, quotes with consent, source-comprehension results and improvement actions—not claims of agronomic effectiveness.

## Open-learning evidence to collect

- Test that an imperfectly phrased question about dairy farming, cows, sheep, pasture, soils, irrigation, weather, effluent or animal health is treated as a learning question rather than a failed paddock lookup.
- Test that a FarmPi observation, deterministic calculation, curated authoritative guidance, research result and general explanation have visibly different provenance labels and do not conflict.
- Test that a question with insufficient farm evidence produces a helpful explanation and boundary, not an invented farm-specific cause, forecast, diagnosis, recommendation or action.
- For each external source eventually integrated, record the organisation, URL/version or retrieval date, topic, review decision and the response wording used to distinguish it from FarmPi data.

## Preserved lessons

- Timestamp ordering mistakes matter: `observed_at`, `received_at`, and database audit time answer different questions. Verify that screen freshness is readable and that exact times/provenance remain in evidence, not routine TTS.
- Test farm-wide phrases independently of prior conversation context: “List the paddocks”, “What paddocks are being monitored?”, and “How many paddocks are there?” must not become a paddock-name lookup.
- Test recovery as learning: unknown/ambiguous paddock phrasing should offer a cautious “Did you mean...?” or valid-name examples, while a known paddock with no reading should report missing data distinctly.
- TLS/SNI matters on the local network: resolve the Pi address but present `farmpi.local` as the HTTPS hostname.
- `Paddock IS` must not become a paddock name in the deterministic router.
- Speech usability matters: contextual `Patek` → `paddock` is visible to the learner rather than hidden.
- Broad conversation must not bypass controlled actions: a natural-language request to rename, calculate, retrieve or make a farm decision still requires the deterministic route and its normal confirmations/evidence.
