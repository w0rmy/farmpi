# Structured requests and routing

Natural language is normalised into a reviewed `QuestionRoute` before data access. It contains intent, paddock subject, measurement key, operation, time window/label, comparison flag, and presentation preference. This keeps compatibility with lexical/regex parsing while giving execution one controlled representation instead of a growing collection of ad hoc database paths.

The router accepts dynamic paddock phrases only as candidates. The deterministic data layer resolves the candidate against active database names; this preserves renamed paddocks such as North Flat. Rename requests remain separate deterministic commands that require a confirmation token and audit row.

Qwen does not choose routes, run SQL, choose a measurement, perform arithmetic, authorise a mutation, or expand an unsupported question. It can only phrase approved verified facts when that improves interaction.

Speech alternatives are passed to `app/speech_normalizer.py` first. It can use the active paddock names and reviewed domain vocabulary to show `Heard` versus `Interpreted`, including the documented contextual `Patek` → `paddock` correction. Typed text is not silently rewritten.
