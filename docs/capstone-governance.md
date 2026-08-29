# Capstone outcome governance

FarmPi is a vehicle for the capstone, not the capstone's end product. Its immutable primary focus is the defined learning outcomes, elective outcomes, and graduate-profile outcomes - especially **Developing Flexible IT Courses** and **AI and Data Sciences**. The farm-monitoring context gives the learning platform a believable real-world purpose; Raspberry Pi, ESP32, LoRa, sensors, databases, synthetic telemetry, and Android plumbing are subordinate enabling context.

## Outcome gate

Before accepting a feature, architecture change, experiment, or evaluation activity, record which outcome it supports and how it will be evidenced. If it supports no outcome, it is out of scope unless it is essential minimal infrastructure. If it reduces accessibility, learner agency, clarity of provenance, teach-by-doing use, or reliable evidence, flag it as negatively affecting the outcomes and redesign or reject it.

This specifically prevents IoT scope creep. More devices, transports, dashboards, control functions, deployment hardening, or model-size work are not progress by themselves. They are only justified when they materially improve the learning platform or provide evidence for the two electives.

## Learning-platform principle

The system should support learning through normal use. A learner should not need to learn FarmPi's command language, database terms, sensor conventions, or prompting technique before they can gain value. Onboarding, examples, explanation depth, evidence visibility, visual presentation, voice/text access, and contextual next steps exist to make ordinary use an embedded learning experience.

Model size is an implementation constraint and optimisation decision. It may affect latency and deployment feasibility, but it is not the capstone thesis.
