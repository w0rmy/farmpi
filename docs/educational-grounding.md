# Educational grounding and flexible learning

FarmPi currently has two separate, labelled sources of grounding:

- **Observational grounding** is validated telemetry and deterministic calculations from MariaDB.
- **Educational grounding** is reviewed, static material in `app/education.py`. It defines a measurement, unit, purpose, limitation, and provenance. It is version controlled and is never invented by Qwen.

Combined questions can present both: a current EC fact remains an observational database result, while “what does it mean?” comes from the EC concept card. Responses identify whether their source category is observational, educational, or combined.

## 27 August 2026 source model

The current two-source model is the alpha baseline, not the final learning boundary. FarmPi is being designed to select the most useful source for a natural agricultural learning question and to say what that source is:

- **FarmPi observation** — validated sensor/database evidence from this farm.
- **Deterministic calculation** — a defined calculation over FarmPi observations.
- **Curated authoritative guidance** — reviewed New Zealand agricultural material, including where relevant DairyNZ, MPI, Earth Sciences New Zealand, and IrrigationNZ or applicable irrigation standards.
- **External research** — current material retrieved when needed, with its source and uncertainty made explicit.
- **General agricultural knowledge** — an explanatory answer that is neither a FarmPi observation nor a claimed authoritative recommendation.

The last three categories are a target architecture, not a statement that live research or broad source integration is already deployed. Until an external source is reviewed and integrated, FarmPi should not fabricate a citation or imply that a named organisation endorses an answer.

Simple, Normal, and Technical are content levels, not merely token limits. They use the same fact but change the instructional material: plain definition, practical measurement context, or technical caveat. More/Normal/Less guidance changes the number of proactive, safe next actions returned by the server.

`GET /api/learning/activities` exposes lightweight teach-by-doing activities. Each has a short instruction, a real question, and one or more successful deterministic route intents. Learner progress is intentionally client-local; FarmPi does not add accounts or an LMS.

The initial activities cover getting started, a named paddock, comparison, a trend, a measurement/unit, provenance, an irrigation-decision boundary, and evidence. A successful activity is based on an actual FarmPi interaction, not a static course-page checkbox.

## Irrigation learning material

`irrigation_decision` is a small, version-controlled concept card. It explains that a current soil-moisture reading is useful evidence but cannot determine an irrigation decision. The approved factors are soil water-holding capacity/field capacity, refill point, recent and expected rainfall, evapotranspiration, soil type, and irrigation-system capacity. When a paddock is named, FarmPi resolves it deterministically and may include only its verified current soil-moisture fact.

This entry is intentionally marked as a curated FarmPi learning draft with NZ source integration pending. No URL or citation has been invented. A later reviewed update can attach DairyNZ or IrrigationNZ material and metadata. The broader learning architecture can also support carefully bounded external research, but that must retain the farm-fact boundary and clearly distinguish researched guidance from a FarmPi observation or decision.

## Guardrail

An association such as rain followed by a moisture increase can be described as a sequence in selected telemetry. FarmPi must not convert it into a causal claim, forecast, diagnosis, recommendation, or agronomic advice about this farm. It may explain relevant general concepts or identified external guidance, but must not blur that explanation with a farm-specific conclusion.
