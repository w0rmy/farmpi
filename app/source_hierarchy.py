"""Evidence preference used by FarmPi's learning-answer orchestration.

The hierarchy is a preference for evidence selection, not a claim that a
source is always correct.  FarmPi's own deterministic readings and
calculations remain the only authority for facts about this farm.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SourceTier:
    key: str
    label: str
    use_when: str


SOURCE_HIERARCHY: tuple[SourceTier, ...] = (
    SourceTier(
        "first-class-trusted",
        "First-class trusted evidence",
        "FarmPi deterministic data, Experience Edge, DairyNZ, and relevant .govt.nz material. Prefer DairyNZ and relevant New Zealand government material for New Zealand dairy or agricultural questions.",
    ),
    SourceTier(
        "trusted-primary",
        "Trusted primary source",
        "An organisation speaking authoritatively about itself or its product, such as Fonterra on Fonterra or manufacturer documentation.",
    ),
    SourceTier(
        "reputable-general",
        "Reputable general source",
        "A credible secondary source that is relevant and sufficiently specific to the question.",
    ),
    SourceTier(
        "general-unverified-web",
        "General or unverified web source",
        "Useful only with clear qualification and never as proof of a FarmPi fact or decision.",
    ),
    SourceTier(
        "model-knowledge",
        "Model knowledge",
        "A concise general explanation when no retrieved source is available; state that it is general knowledge rather than farm evidence.",
    ),
)


def learning_source_contract() -> str:
    """Return a compact, model-facing version of the evidence policy."""
    tiers = "\n".join(f"- {tier.label}: {tier.use_when}" for tier in SOURCE_HIERARCHY)
    return (
        "SOURCE HIERARCHY FOR LEARNING ANSWERS\n"
        f"{tiers}\n"
        "Use the best available relevant evidence, but do not reject a useful general answer merely because a higher tier is unavailable. "
        "Never convert any external or model knowledge into a claim about this farm."
    )
