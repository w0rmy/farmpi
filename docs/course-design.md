# FarmPi embedded flexible IT course design

## Purpose and learner profile

This short course is for non-specialist FarmPi users who need to use an information-rich application confidently, interpret its evidence, and use AI support without treating it as automatic authority. Farm monitoring is the authentic technical vehicle; the assessed contribution is primarily **Developing Flexible IT Courses**, with governed AI/data use contributing to **AI and Data Sciences**.

## Aim and outcomes

**Aim:** teach a non-specialist user how to use and understand FarmPi, find and interpret information, use AI-supported learning tools, solve common usage or interpretation problems, and find or check further help when needed.

1. **LO1:** navigate and use core FarmPi functions and adjust available accessibility/presentation settings.
2. **LO2:** understand statuses, information, charts, evidence, and monitoring information sufficiently to use the app effectively.
3. **LO3:** use the AI assistant in ordinary language, request simpler/deeper/alternative explanations, ask follow-ups, and find further help.
4. **LO4:** solve common problems using the course, app, evidence, and AI support while recognising AI limitations and checking important information.

## Constructive alignment and module map

| Module | Main outcomes | Authentic Try evidence | Check/continuation |
|---|---|---|---|
| 1. Getting Started | LO1 | Guide me / ordinary-language exploration | Choose a helpful presentation setting; continue to information interpretation. |
| 2. Understanding the Application | LO1, LO2 | Request a comparison and inspect chart/evidence | Distinguish observation from deterministic calculation. |
| 3. Using the AI Learning Assistant | LO3, LO4 | Ask for a concept explanation and adapt it | State when important information needs checking. |
| 4. Getting Help and Solving Problems | LO3, LO4 | Rephrase/recover and inspect provenance | Name a clarification and verification strategy. |
| 5. Putting It Together | LO1–LO4 | Complete a trend/comparison enquiry, inspect evidence, seek an explanation, name a check | Reflect on the end-to-end evidence-informed task; revisit freely. |

Every module uses the same visible **Learn → Try → Ask → Check → Continue** pattern. Try completion comes from a real returned FarmPi intent where possible; Check is a lightweight self-reflection, not grading. Module 5 is an authentic whole-app activity rather than a large multiple-choice assessment.

## Flexible pathways and accessibility

The recommended five-module sequence gives novices a safe starting path, while all modules remain directly openable. Local-only progress remembers the current module plus completed Try/check/module markers across restarts. It deliberately has no accounts, cloud sync, grades, badges, learner profiling, or learning analytics.

The existing six themes, compact/standard/large text-size choices, explanation-depth setting, guidance-frequency setting, chart representations, typed/speech input, and spoken output apply to the course as to the rest of the app. They offer learner choice and presentation flexibility, but do not establish a claim of accessibility compliance.

## AI role, limits, and evidence

The Android client may send a validated module id with an ordinary `/api/ask` request. The server accepts only an id from its controlled course definition and adds only the matching reviewed context to a model-assisted response; clients cannot supply course/system prompt text. That contribution is disclosed in provenance.

AI is used for explanation, language interpretation, and conversational follow-up. It is not automatically correct and has no authority over FarmPi observations, calculations, identity, or actions. Learners are explicitly taught to distinguish model knowledge from deterministic FarmPi evidence and to check important information. FarmPi has no live web-search feature: source-oriented responses state that limit.

## Evaluation approach and rationale

The design reuses the project’s established embedded-learning, learner-agency, adaptation, provenance, and deterministic-authority approach. Evaluation combines automated contracts (course integrity, controlled context, intent completion) with consented task observation: can a non-specialist start, follow or depart from the pathway, interpret evidence, use/verify AI explanations, recover from misunderstanding, and choose useful presentation settings? Results must be recorded rather than assumed. Detailed checks are maintained in [testing-and-evaluation.md](testing-and-evaluation.md).

## Scope control

This is a bounded course spine over existing FarmPi capabilities. It adds no LMS, account, cloud data, gamification, autonomous agent, uncontrolled AI-authored course content, new monitoring/control feature, sensor/network work, or unrelated visual-art work. The governing outcome gate remains in [capstone-governance.md](capstone-governance.md).
