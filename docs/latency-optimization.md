# FarmPi local-LLM latency optimisation

## Purpose

The Raspberry Pi 4 proof of concept is functionally successful, but local Qwen3 0.6B inference remains the dominant source of user-visible latency. This optimisation pass keeps the same grounded architecture while reducing unnecessary work and adding measurements so later hardware and software decisions can be supported by evidence.

The optimisation does not move factual reasoning into the LLM. MariaDB and deterministic Python functions remain authoritative.

The 27 August 2026 open-learning architecture does not change this deterministic farm-data path. It adds separate, provenance-aware learning-source selection for questions that do not require a farm lookup or action. Curated-source retrieval, external research when implemented, and source rendering must be timed and evaluated as distinct stages; they must not be hidden inside `llm_ms` or represented as verified FarmPi data.

## Changes implemented

### 1. Per-request timing

`POST /api/ask` now measures and returns:

- `routing_ms` — deterministic question classification time;
- `database_ms` — MariaDB retrieval plus deterministic farm-data calculation time;
- `context_ms` — verified-context and LLM payload construction time;
- `llm_ms` — request/response time for `llama-server`;
- `total_ms` — complete FastAPI request processing time.

The same timings are written to the Uvicorn/FarmPi service log. During alpha testing the browser displays total and LLM time after each answer.

These measurements are intended to show where latency actually occurs rather than assuming MariaDB, FastAPI, or the model is responsible.

### 2. Deterministic question router

`app/question_router.py` performs a small, explicit classification before FarmPi builds LLM context. Current routes are:

- `driest`;
- `wettest`;
- `average`;
- `paddock` for a named paddock's soil-moisture value;
- `paddock-field` for a named paddock's current air temperature, relative humidity, soil pH, or light value;
- `measurement-fallback` for a current environmental-measurement snapshot when no paddock is named;
- `unsupported` for weather, advice, causal questions, daylight-hour aggregates, and non-approved aggregates;
- `moisture-fallback` for broader or unclassified soil-moisture questions.

The router does not generate SQL and does not ask Qwen to choose a database query. It selects from approved deterministic application functions.

The expanded alpha now uses the measurement catalogue for aliases and allowed operations, resolves current paddock names dynamically, and has bounded historical routes. A rename confirmation is answered directly by the application and does not invoke the LLM, so mutation latency is not confused with model latency.

### 3. Context slimming

Previously every question received the complete current soil-moisture snapshot, farm average, driest result, wettest result, timestamps, and explanatory text.

For a question such as:

```text
Which paddock is driest?
```

FarmPi now supplies only the verified result needed for that route, conceptually:

```text
VERIFIED FACTS
- Driest paddock: Paddock A.
- Soil moisture: 18.00%.
```

A paddock-specific question receives only that paddock's verified latest complete current value. This applies to all catalogued fields, including EC, rainfall, pressure, wind, pasture height, and leaf wetness; Qwen never chooses the field or calculates a value. The complete moisture snapshot is retained as a fallback for broader questions and comparisons.

This is important on the Raspberry Pi 4 because prompt evaluation is substantially slower than on desktop-class hardware. Reducing unnecessary prompt tokens can therefore reduce response time without weakening grounding.

### 4. Shorter generation budget

The system prompt is now deliberately compact and `max_tokens` for ordinary answers has been reduced from 80 to 40. Qwen remains responsible for rendering the deterministic result into natural language, but it is encouraged to answer briefly.

### 5. Persistent llama-server HTTP connection

FastAPI now keeps one `httpx.AsyncClient` open for the lifetime of the application instead of creating a new client for every request. This removes repeated connection setup. It is a minor optimisation compared with model inference, but it is simple and appropriate.

## Grounding path after optimisation

```text
User question
    ↓
Deterministic question router
    ↓
Approved MariaDB/Python operation
    ↓
Small structured verified result
    ↓
Compact LLM context
    ↓
Qwen3 0.6B
    ↓
Brief natural-language answer
```

Qwen still cannot query MariaDB directly and is not asked to calculate farm statistics. Open agricultural explanation does not authorise it to create a farm-specific fact, decision or action.

## Test method

After deployment, use the same question several times so context reuse and normal run-to-run variation can be observed. Recommended initial tests are:

```text
Which paddock is driest?
Which paddock is wettest?
What is the average soil moisture?
What is Paddock B's soil moisture?
What is Paddock B's air temperature?
What is Paddock B's humidity?
What is Paddock B's soil pH?
What is the light level in Paddock B?
Compare Paddock A and Paddock B.
```

For each request, record the returned timing fields or inspect the service log:

```bash
journalctl -u farmpi.service -n 50 --no-pager
```

A useful comparison should include several repeated runs of the same short question rather than relying on a single response.

## Interpretation

The expected result is that `database_ms`, `routing_ms`, and `context_ms` remain small compared with `llm_ms`. If that is confirmed, the evidence supports the conclusion that the Raspberry Pi 4 CPU inference path, rather than MariaDB or the application architecture, is the primary latency constraint.

No performance improvement should be claimed in the capstone until before-and-after measurements have been collected. The purpose of this instrumentation is to provide that evidence.
