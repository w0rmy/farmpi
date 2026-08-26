# Structured requests and routing

Natural language is normalised into a reviewed `QuestionRoute` before data access. It contains intent, paddock subject, measurement key, operation, time window/label, comparison flag, and presentation preference. This keeps compatibility with lexical/regex parsing while giving execution one controlled representation instead of a growing collection of ad hoc database paths. The approved intents include `farm_inventory_count`, `paddock_summary`, current paddock measurements, and a short `contextual-follow-up` route as well as the original analytics and administration routes.

The router accepts dynamic paddock phrases only as candidates. The canonical deterministic resolver checks active current names, audited prior names, canonical letter forms, then numeric/word-number forms. Numeric aliases use the active MariaDB paddock order: `Paddock 1` is the first active paddock, `Paddock 2` the second, and so on. This remains true after a rename, so if the original Paddock B becomes North Flat, `Paddock 2` and the audited alias `Paddock B` still resolve to North Flat's stable numeric identity. Invalid or ambiguous references produce a specific clarification with active-name suggestions.

The API returns an opaque `conversation_id`. Web and Android send it on the next request, which allows the small 30-minute in-memory context to turn `What about Paddock 2?` into the immediately preceding supported paddock measurement or summary. It is not general chat memory and does not add any authority to Qwen.

Qwen does not choose routes, run SQL, choose a measurement, perform arithmetic, authorise a mutation, or expand an unsupported question. It can only phrase approved verified facts when that improves interaction.

Speech alternatives are passed to `app/speech_normalizer.py` first. It can use the active paddock names and reviewed domain vocabulary to show `Heard` versus `Interpreted`, including the documented contextual `Patek` → `paddock` correction. Typed text is not silently rewritten.
