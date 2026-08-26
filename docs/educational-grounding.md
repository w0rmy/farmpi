# Educational grounding and flexible learning

FarmPi has two separate, labelled sources of grounding:

- **Observational grounding** is validated telemetry and deterministic calculations from MariaDB.
- **Educational grounding** is reviewed, static material in `app/education.py`. It defines a measurement, unit, purpose, limitation, and provenance. It is version controlled and is never invented by Qwen.

Combined questions can present both: a current EC fact remains an observational database result, while “what does it mean?” comes from the EC concept card. Responses identify whether their source category is observational, educational, or combined.

Simple, Normal, and Technical are content levels, not merely token limits. They use the same fact but change the instructional material: plain definition, practical measurement context, or technical caveat. More/Normal/Less guidance changes the number of proactive, safe next actions returned by the server.

`GET /api/learning/activities` exposes lightweight teach-by-doing activities. Each has a short instruction, a real question, and one or more successful deterministic route intents. Learner progress is intentionally client-local; FarmPi does not add accounts or an LMS.

The initial activities cover getting started, a named paddock, comparison, a trend, a measurement/unit, provenance, unavailable boundaries, and evidence. A successful activity is based on an actual FarmPi interaction, not a static course-page checkbox.

## Guardrail

An association such as rain followed by a moisture increase can be described as a sequence in selected telemetry. FarmPi must not convert it into a causal claim, forecast, diagnosis, recommendation, or agronomic advice.
