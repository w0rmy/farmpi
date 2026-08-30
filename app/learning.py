"""Controlled FarmPi course content and compatible teach-by-doing activities.

The course is deliberately data in source control, rather than model-generated
content. It supplies a small learning spine around normal FarmPi use; it is not
an LMS, assessment engine, or learner profile.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class LearningActivity:
    """A real FarmPi interaction that can demonstrate a Try step."""

    id: str
    title: str
    instruction: str
    example_question: str
    success_intents: tuple[str, ...]


@dataclass(frozen=True)
class LearningOutcome:
    id: str
    statement: str


@dataclass(frozen=True)
class UnderstandingCheck:
    prompt: str
    reflection_hint: str


@dataclass(frozen=True)
class CourseModule:
    """A reviewed module following Learn -> Try -> Ask -> Check -> Continue."""

    id: str
    title: str
    learning_outcomes: tuple[str, ...]
    learn_content: str
    try_activity: LearningActivity
    ai_quick_prompts: tuple[str, ...]
    understanding_check: UnderstandingCheck
    continue_content: str
    next_module_id: str | None
    response_intents: tuple[str, ...]
    prompt_context: str


COURSE_ID = "farmpi-flexible-it-course"
COURSE_TITLE = "Using FarmPi to learn with information, evidence, and AI support"
COURSE_AIM = (
    "Teach a non-specialist user how to use and understand FarmPi, find and interpret information, "
    "use the AI-supported learning tools, solve common usage or interpretation problems, and find or check further help when needed."
)

LEARNING_OUTCOMES = (
    LearningOutcome("LO1", "Navigate and use the main FarmPi functions and adjust available accessibility and presentation settings."),
    LearningOutcome("LO2", "Understand the main information, statuses, charts, evidence, and monitoring information sufficiently to use the application effectively."),
    LearningOutcome("LO3", "Use the AI learning assistant in ordinary language, request alternative, deeper, or simpler explanations, ask follow-ups, and find further learning or help."),
    LearningOutcome("LO4", "Use the course, app, evidence, and AI support to solve common problems while recognising AI limitations and checking important information where appropriate."),
)

MODULES = (
    CourseModule("getting-started", "Getting Started with FarmPi", ("LO1",),
        "What is FarmPi?\nFarmPi helps you use the farm-monitoring application and understand the information it provides. You can use this course, ask FarmPi questions in your own words, and move between the two whenever you need to.\n\nYou do not need special commands. If an explanation does not help, ask FarmPi to explain it differently, give more detail, or help you decide what to look at next.\n\nTry it now: find Ask and Learn at the bottom of the screen. Open each area, then return to Ask.\n\nFind your way around\nAsk is where you type or speak to FarmPi. Learn is this course. The settings cog lets you change learning and presentation preferences. The status message tells you whether FarmPi is available. FarmPi is already connected for this module; you only need to recognise the status, not configure a connection.\n\nAsk your first question\nType naturally, for example: “What can FarmPi help me with?” You can also use the microphone. FarmPi can speak its reply; use Stop while it is speaking if you want it to stop.\n\nUse Guide me and follow-up questions\nYou do not need to know exactly what to ask. Press Guide me, choose a suggested question, then choose a follow-up after the response.\n\nAdjust FarmPi to suit you\nIn Settings, choose Explanation depth: Simple, Normal, or Technical; Guidance: More, Normal, or Less; a theme such as Neutral, NZ red, white and blue, Green / natural, Dark high contrast, Yellow / black, or Muted / low stimulation; and Text size: Compact, Standard, or Large. These settings change how FarmPi presents learning. They do not change the underlying facts or the learning outcome.",
        LearningActivity("getting-started", "Try the FarmPi controls", "Return to Ask and type “What can FarmPi help me with?” Then ask a question with the microphone and use Stop while FarmPi is speaking. Press Guide me, choose a suggested question and then a follow-up. In Settings, change text size and theme. Ask a similar question once at Simple and once at Technical explanation depth, compare the two presentations, and keep the settings you prefer.", "What can FarmPi help me with?", ("capability",)),
        ("Explain what FarmPi can help me with more simply.", "Give the same explanation with more technical detail."),
        UnderstandingCheck("Quick self-check: Can you move between Ask and Learn, type a question, use the microphone, use Guide me, change explanation depth, and change text size or theme?\n\nIf FarmPi's explanation is too technical, what can you change?\nIf you are not sure what to ask next, what can you use?", "This is not a quiz or grade. Check the controls in the app: change Explanation depth for a simpler presentation, and use Guide me for suggested next questions."),
        "You now know how to interact with FarmPi and adjust the learning experience to suit you. In the next module, you will learn how to understand the information FarmPi shows you.",
        "understanding-the-application", ("capability",),
        "The learner is beginning the course. Help them use ordinary language, Guide me, voice and settings without implying that settings change FarmPi facts or teaching connection administration."),
    CourseModule("understanding-the-application", "Understanding the Application", ("LO1", "LO2"),
        "A FarmPi answer can include a current observation, a deterministic calculation, a chart, evidence, and source provenance. These are different kinds of information: inspect the evidence and chart before drawing a conclusion.",
        LearningActivity("comparison", "Compare and inspect evidence", "Compare a measurement across paddocks, then open the chart and sources or evidence.", "Compare soil EC across all paddocks.", ("comparison", "ranking", "historical", "farm-average")),
        ("What does soil EC mean?", "How should I read a FarmPi chart?"),
        UnderstandingCheck("What is the difference between a FarmPi observation and a deterministic comparison?", "Use the evidence panel and chart labels to find the information you need."),
        "Continue to use the evidence panel and chart labels before drawing a conclusion. The next module focuses on using AI explanations carefully.",
        "using-the-ai-learning-assistant", ("historical", "comparison", "ranking", "farm-average", "driest", "wettest", "education"),
        "The learner is practising information interpretation. Explain the distinction between observations, deterministic calculations, charts, and provenance; do not turn them into an unsupported farm conclusion."),
    CourseModule("using-the-ai-learning-assistant", "Using the AI Learning Assistant", ("LO3", "LO4"),
        "Ask naturally and continue with follow-up questions such as 'more simply', 'more detail', or 'give me an example'. AI can explain and be challenged, but it is not automatically correct. FarmPi's deterministic evidence and calculations are different from model knowledge, so check important information.",
        LearningActivity("measurement", "Ask and adapt an explanation", "Ask what a measurement means, then ask for a simpler, deeper, or example-based explanation.", "What does soil EC mean?", ("education", "agriculture-learning", "conversation")),
        ("Explain soil EC more simply.", "Give me an example of checking an AI explanation against FarmPi evidence."),
        UnderstandingCheck("When would you check an AI answer against FarmPi evidence or another reliable source?", "A useful answer names the decision or claim that matters and the evidence you would check."),
        "Next, practise recovering from an unclear answer and finding help or provenance.",
        "getting-help-and-solving-problems", ("education", "agriculture-learning", "agriculture-research", "conversation"),
        "The learner is learning how to use AI support responsibly. Encourage ordinary-language questions and follow-ups, clearly distinguish model explanation from FarmPi evidence, and prompt checking of important information."),
    CourseModule("getting-help-and-solving-problems", "Getting Help and Solving Problems", ("LO3", "LO4"),
        "If FarmPi misunderstands a question, rephrase it, name the paddock or measurement, use the visible evidence, or ask for clarification. For important claims, use the source/provenance panel and remember that this prototype does not perform live web searches.",
        LearningActivity("provenance", "Recover and check help", "Ask about simulated data or a source, then inspect the source or evidence panel.", "Explain simulated data.", ("education", "semantic-clarification", "agriculture-research", "agriculture-learning")),
        ("I do not understand that answer. Can you say it another way?", "Where can I check this important information?"),
        UnderstandingCheck("What could you do if FarmPi gives an answer that is unclear or important to verify?", "Think of one way to clarify the question and one way to inspect or check the answer."),
        "Next, bring the course ideas together in one evidence-informed enquiry.",
        "putting-it-together", ("semantic-clarification", "contextual-follow-up", "agriculture-research", "agriculture-learning"),
        "The learner is practising recovery and help-seeking. Offer a concise rephrasing or clarification path, and make source limits and important-information checking explicit."),
    CourseModule("putting-it-together", "Putting It Together", ("LO1", "LO2", "LO3", "LO4"),
        "Use the whole application for one authentic task: ask a farm-data question, inspect its chart or evidence, ask the AI to explain what you found, and state what you would check before using it for an important decision.",
        LearningActivity("evidence", "Complete an evidence-informed enquiry", "Ask for a trend or comparison, inspect evidence, then ask for an explanation and identify a sensible check.", "Show a graph of soil moisture over the last 24 hours.", ("historical", "comparison", "ranking", "education", "agriculture-learning")),
        ("Help me interpret this chart without making a farm decision for me.", "What should I check before acting on this information?"),
        UnderstandingCheck("Describe the evidence you used, what the AI helped explain, and one thing you would check next.", "This is a reflection, not a graded assessment. Return to earlier modules whenever useful."),
        "You have reached the end-to-end activity. Return to any module whenever it helps with your next question.",
        None, ("historical", "comparison", "ranking", "education", "agriculture-learning"),
        "The learner is completing an end-to-end evidence-informed task. Help them interpret the available information without making a decision for them, and ask them to name an appropriate next check."),
)

MODULE_BY_ID = {module.id: module for module in MODULES}
OUTCOME_IDS = frozenset(outcome.id for outcome in LEARNING_OUTCOMES)


def module_for_id(module_id: str) -> CourseModule | None:
    """Return reviewed module data, never caller-provided prompt material."""
    return MODULE_BY_ID.get(module_id)


def course_payload() -> dict[str, object]:
    """Return the deterministic API representation of the reviewed course."""
    return {
        "id": COURSE_ID,
        "title": COURSE_TITLE,
        "aim": COURSE_AIM,
        "learning_outcomes": [asdict(outcome) for outcome in LEARNING_OUTCOMES],
        "modules": [
            {"id": module.id, "title": module.title, "learning_outcomes": list(module.learning_outcomes),
             "learn_content": module.learn_content,
             "try": {**asdict(module.try_activity), "success_intents": list(module.try_activity.success_intents)},
             "ai_quick_prompts": list(module.ai_quick_prompts), "understanding_check": asdict(module.understanding_check),
             "continue_content": module.continue_content, "next_module_id": module.next_module_id,
             "response_intents": list(module.response_intents)}
            for module in MODULES
        ],
    }


# Compatibility endpoint content. Existing clients retain the wider concise
# catalogue while the course remains the single canonical learning structure.
ACTIVITIES = (
    MODULES[0].try_activity,
    LearningActivity("one-paddock", "Ask about one paddock", "Ask for a current value in one paddock.", "What is Paddock A's soil EC?", ("paddock", "paddock-field")),
    MODULES[1].try_activity,
    LearningActivity("driest", "Find a moisture extreme", "Find the driest or wettest paddock from verified readings.", "Which paddock is driest?", ("driest", "wettest")),
    LearningActivity("trend", "Inspect a 24-hour trend", "Ask for a deterministic trend over a time period.", "How has Paddock A soil moisture changed over the last 24 hours?", ("historical",)),
    MODULES[2].try_activity,
    MODULES[3].try_activity,
    LearningActivity("irrigation-factors", "Understand an irrigation decision", "See the current soil moisture, then learn why FarmPi cannot make the decision from that reading alone.", "Should I irrigate Paddock A?", ("irrigation-decision",)),
    MODULES[4].try_activity,
)


def activity_payload() -> list[dict[str, object]]:
    return [asdict(activity) for activity in ACTIVITIES]
