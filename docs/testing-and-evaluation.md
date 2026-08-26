# Testing, capstone evidence, and evaluation

The automated Python suite covers measurement ranges, telemetry clock semantics, sequence retry/idempotency, dynamic paddock names, speech normalisation, confirmation-only rename, existing deterministic grounding, and the repeatable database update contract. New analytics must be tested with controlled row fixtures for calculation, selected period, chart series, and evidence metadata; they must never require Qwen.

Before a major feature is considered complete, update the affected text, Mermaid diagram source, tests, rationale, limitations, and user-facing instructions. Keep any rendered diagram export alongside its `.mmd` source when a formal document needs a portable image.

## Initial usability / learning test plan

Recruit a small number of nontechnical learners after deployment; do not fabricate results. Observe whether participants can understand simulated provenance, ask a one-paddock question, compare paddocks, interpret a graph/evidence panel, and recognise an unavailable recommendation boundary. Compare Simple and Technical explanations for clarity, note SpeechRecognizer mishearings and normaliser corrections, and ask whether More/Normal/Less guidance feels excessive or insufficient. Record task completion, confusion points, quotes with consent, and improvement actions—not claims of agronomic effectiveness.

## Preserved lessons

- Timestamp ordering mistakes matter: `observed_at`, `received_at`, and database audit time answer different questions.
- TLS/SNI matters on the local network: resolve the Pi address but present `farmpi.local` as the HTTPS hostname.
- `Paddock IS` must not become a paddock name in the deterministic router.
- Speech usability matters: contextual `Patek` → `paddock` is visible to the learner rather than hidden.
