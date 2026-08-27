"""Curated New Zealand agricultural source directory and provenance helpers.

These records are source metadata, not a web-search engine. FarmPi may use reviewed
claims included here and may direct learners to the source. It must not imply that a
live page was searched unless a future research provider actually performed retrieval.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class KnowledgeSource:
    key: str
    name: str
    organisation: str
    url: str
    topics: tuple[str, ...]
    authority: str
    reviewed_claims: tuple[str, ...] = ()

    def public_dict(self) -> dict[str, object]:
        return asdict(self)


SOURCES: tuple[KnowledgeSource, ...] = (
    KnowledgeSource(
        "dairynz-irrigation",
        "Irrigation scheduling",
        "DairyNZ",
        "https://www.dairynz.co.nz/environment/irrigation/scheduling/",
        ("irrigation", "soil moisture", "field capacity", "refill point", "evapotranspiration", "water"),
        "authoritative-nz-industry",
        (
            "DairyNZ irrigation scheduling considers soil temperature, soil moisture relative to refill point and field capacity, expected rain, water restrictions, effluent, stock, irrigation-system capacity and evapotranspiration.",
            "DairyNZ describes soil-moisture monitoring as an important input to irrigation scheduling rather than a complete irrigation decision by itself.",
        ),
    ),
    KnowledgeSource(
        "dairynz",
        "DairyNZ farming information",
        "DairyNZ",
        "https://www.dairynz.co.nz/",
        ("dairy", "cow", "cattle", "milk", "mastitis", "milk fever", "pasture", "calf", "calving", "feed", "grazing"),
        "authoritative-nz-industry",
    ),
    KnowledgeSource(
        "mpi-animal-welfare",
        "Animal welfare codes",
        "Ministry for Primary Industries (MPI)",
        "https://www.mpi.govt.nz/animals/animal-welfare/codes/all-animal-welfare-codes",
        ("animal welfare", "welfare", "cow", "cattle", "calf", "sheep", "beef", "livestock", "regulation", "code"),
        "authoritative-nz-government",
        (
            "MPI states that people responsible for dairy cattle, sheep and beef cattle need to comply with relevant animal-welfare minimum standards and the Animal Welfare Act.",
        ),
    ),
    KnowledgeSource(
        "mpi-sheep-beef-code",
        "Code of Welfare: Sheep and Beef Cattle",
        "Ministry for Primary Industries (MPI)",
        "https://www.mpi.govt.nz/animals/animal-welfare/codes/all-animal-welfare-codes/code-of-welfare-sheep-and-beef-cattle",
        ("sheep", "beef", "lamb", "ewe", "ram", "welfare"),
        "authoritative-nz-government",
    ),
    KnowledgeSource(
        "earth-sciences-nz",
        "Earth Sciences New Zealand data and applications",
        "Earth Sciences New Zealand",
        "https://www.earthsciences.nz/data-and-applications",
        ("weather", "climate", "rain", "rainfall", "drought", "soil moisture", "hydrology", "water", "forecast", "el nino"),
        "authoritative-nz-science",
    ),
    KnowledgeSource(
        "irrigationnz-soil-moisture",
        "Soil Moisture Monitoring",
        "Irrigation New Zealand",
        "https://www.irrigationnz.co.nz/Members%20Only/good%20management%20practice/Book11-SoilMM.pdf",
        ("irrigation", "soil moisture", "sensor", "volumetric", "soil water", "monitoring"),
        "authoritative-nz-industry",
        (
            "Irrigation New Zealand distinguishes gravimetric soil-water content, volumetric soil-water content and soil-water potential, and notes that most field techniques are indirect measurements whose interpretation depends on the measurement method.",
        ),
    ),
)


def sources_for_question(question: str, limit: int = 4) -> tuple[KnowledgeSource, ...]:
    """Select relevant reviewed NZ sources by topic without claiming live retrieval."""
    lowered = question.casefold()
    scored: list[tuple[int, KnowledgeSource]] = []
    for source in SOURCES:
        score = sum(3 if topic in lowered else 0 for topic in source.topics)
        # Organisation names are strong explicit-source signals.
        if source.organisation.casefold() in lowered or source.key.split("-")[0] in lowered:
            score += 5
        if score:
            scored.append((score, source))
    if not scored:
        # General agricultural learning gets a small NZ source directory rather
        # than pretending a specific source supports an unrelated claim.
        scored = [(1, source) for source in SOURCES if source.key in {"dairynz", "mpi-animal-welfare"}]
    scored.sort(key=lambda item: (-item[0], item[1].name))
    return tuple(source for _, source in scored[:limit])


def format_source_context(question: str) -> tuple[str, tuple[KnowledgeSource, ...]]:
    """Return source metadata plus only the reviewed claims actually stored here."""
    sources = sources_for_question(question)
    lines = [
        "CURATED NEW ZEALAND SOURCE DIRECTORY",
        "These are reviewed source references. Do not say they were searched live. Attribute only an explicit 'Reviewed claim' below to the named organisation; a source listed without a reviewed claim is a reference suggestion, not evidence for your answer.",
    ]
    for source in sources:
        lines.append(f"- {source.organisation}: {source.name} — {source.url}")
        for claim in source.reviewed_claims:
            lines.append(f"  Reviewed claim: {claim}")
    return "\n".join(lines), sources


def provenance_for_sources(sources: tuple[KnowledgeSource, ...]) -> list[dict[str, str]]:
    """Make source use inspectable without overstating unsupported attribution."""
    return [
        {
            "kind": "authoritative-curated",
            "organisation": source.organisation,
            "title": source.name,
            "url": source.url,
            "authority": source.authority,
            "use": "reviewed-claim-support" if source.reviewed_claims else "reference-only",
        }
        for source in sources
    ]
