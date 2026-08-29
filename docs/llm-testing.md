# FarmPi LLM Testing – Raspberry Pi and Reference-Model Findings

## Reference-model pivot — 27 August 2026

The earlier sections of this document are retained as the chronological record of Raspberry Pi model testing. Their performance measurements remain useful, but one architectural conclusion has now changed substantially.

Early testing assumed the LLM could remain a very tightly constrained language renderer over deterministic farm results. Subsequent end-to-end learner testing showed that this was **too restrictive for the Flexible IT Training objective**. A 0.6B model could return short known facts quickly, but natural paraphrases, polite/indirect requests, follow-up language, speech variation and broad agricultural learning exposed both router brittleness and limited language capacity.

The current development/reference model is therefore **Qwen3.5-9B Q4_K_M hosted by LM Studio on the Windows development PC**, while the Raspberry Pi continues to own FarmPi application logic, MariaDB, deterministic analytics and the learner API. This is an experiment/development topology, not a decision that the final capstone must require a PC-hosted model.

The reference model is used to answer a different question from the original Pi benchmark:

> What should FarmPi feel like when the language layer is capable enough that architectural problems are not confused with small-model language limitations?

Current Qwen3.5-9B observations include approximately **24 generated tokens/second** on the RTX 3070 test PC. Thinking/reasoning was disabled in the LM Studio Qwen3.5 chat template because a 30-token FarmPi response was initially consumed entirely by reasoning tokens and returned an empty visible answer. With thinking disabled, the same server generated normal visible output at approximately 24 tokens/second.

The FarmPi response ceilings have subsequently been increased from `30 / 40 / 70` to `64 / 96 / 128` tokens for Simple / Normal / Technical explanations. These remain maximum ceilings: FarmPi still requests short answers and one useful learning direction.

The development strategy is now:

```text
Qwen3.5-9B reference model
        ↓
make FarmPi conversationally and educationally correct
        ↓
build a repeatable conversational/learning test suite
        ↓
re-test Qwen3 1.7B and smaller Pi-hosted models
        ↓
choose the smallest deployment model that preserves an acceptable learner experience
```

This prevents two different failure classes from being confused:

- **architecture failure** — FarmPi routes or guardrails reject valid learner language;
- **model-capacity failure** — the application gives the model an appropriate task but the model cannot reliably understand/render it.

The strong deterministic boundaries remain. Qwen does not calculate FarmPi statistics, invent sensor readings, resolve database identity, authorise a rename or directly mutate MariaDB. What has changed is that the language model is now allowed to play a much broader role in **semantic learner-intent interpretation and agricultural education**.

Accordingly, statements later in this historical document that the LLM need not act as a broad farming educator should be read as the **earlier design hypothesis**, not the current architecture. FarmPi is now intended to teach broad practical agriculture while keeping farm-specific facts/actions separately controlled and provenance-labelled.

---

## 16-paddock synthetic-data stage

The next alpha stage turns the connected ESP32 into a 16-node synthetic telemetry generator. This expands the data available for AI/Data Science and Flexible Learning evaluation without claiming real agronomy. The experiment deliberately keeps pressure, rainfall, soil moisture, light, EC, temperature and pasture-height relationships in deterministic application/firmware code; Qwen only receives verified results. This provides a useful evaluation dataset while preserving the original conclusion that the local model should not calculate farm facts, propose irrigation, or make causal agricultural claims.

## Purpose

The purpose of this testing was to determine whether an existing Raspberry Pi 4 could provide a practical platform for running a lightweight large language model locally as part of the farm-monitoring capstone project.

The intended role of the LLM is not to perform statistical calculations or independently analyse raw sensor data. Deterministic application software will retrieve and calculate verified results, while the LLM will provide the natural-language interface between those results and the user.

The initial question was therefore whether a Raspberry Pi 4 could run a sufficiently capable LLM at an acceptable speed for an interactive user interface.

## Known-Good Alpha Milestone — 26 August 2026

The complete local AI proof-of-concept chain is now working and is recorded as a **known-good alpha milestone**:

```text
Android phone / browser
        ↓ HTTPS (Caddy internal CA)
Caddy reverse proxy
        ↓ http://127.0.0.1:8000
FastAPI application and grounding/control layer
        ↓ http://127.0.0.1:8080
llama-server (Qwen3 0.6B, reasoning off)
        ↓
Grounded response to the browser
```

The following behaviours have been verified:

- Android/browser access over HTTPS works through Caddy;
- Caddy's reverse proxy and internal CA HTTPS configuration work;
- FastAPI listens locally on `127.0.0.1:8000` and `llama-server` listens locally on `127.0.0.1:8080`;
- FastAPI supplies the system constraints and verified, hard-coded prototype farm data before calling the LLM;
- Qwen3 0.6B runs with reasoning disabled;
- browser speech input (`en-NZ`) and browser text-to-speech output work;
- the FarmPi application and local LLM are enabled as systemd services;
- `GET /health` remains a lightweight service check, while the LLM status check confirms whether the local model is reachable;
- supported questions grounded in the supplied farm data are answered correctly; and
- requests for out-of-scope data are rejected rather than answered with invented information.

This is a deliberately constrained alpha, not yet a live farm-data system. The next architectural step is to replace hard-coded data with a small deterministic MariaDB-backed data layer. The first iteration should define simple `paddocks`, `sensors`, and `readings` data, then expose a deterministic function such as `get_driest_paddock()` for the grounding layer to use.

## Test Platform

The initial test platform was:

- Raspberry Pi 4
- 8 GB RAM
- Raspberry Pi OS Lite 64-bit
- Debian Trixie base
- headless operation
- `llama.cpp` inference engine
- browser-based access through `llama-server`
- Android phone used as the client
- local network access only

The Raspberry Pi had approximately 7.6 GiB usable RAM and a 2 GiB swap file.

## Initial LLM Test – Qwen3 1.7B

The first substantial model tested was:

- Qwen3 1.7B
- Instruct/chat model
- Q4_K_M quantisation
- GGUF model format
- `llama.cpp` inference engine
- 2048-token context

The model loaded successfully and could be accessed remotely from an Android phone through the `llama-server` web interface.

This proved that an 8 GB Raspberry Pi 4 is technically capable of hosting and serving a local LLM.

### Resource Usage

During inference, `llama-server` typically consumed approximately:

- 377–397% CPU
- approximately 1.5 GB resident memory
- approximately 20% of total system RAM
- no swap

The CPU figure represents almost complete utilisation of all four Raspberry Pi CPU cores.

Typical system utilisation during generation was approximately:

```text
CPU user time: 94–99%
CPU idle:      0.7–5%
llama-server:  approximately 380–397% CPU
```

Memory was not a limiting factor. Several gigabytes of RAM remained available throughout testing.

The principal limitation was therefore CPU processing capacity rather than memory capacity.

## Power and Throttling Test

Initial testing reported:

```text
throttled=0x50000
```

The Raspberry Pi was being powered from a battery power pack at the time. This indicated that an undervoltage/throttling event had occurred since boot.

The power pack was replaced with the official Raspberry Pi power supply and the system was rebooted.

The subsequent result was:

```text
throttled=0x0
```

This confirmed that neither undervoltage nor thermal throttling was affecting the subsequent performance tests.

Operating temperature was approximately:

```text
48.2°C
```

Temperature was therefore not considered a performance limitation.

## Qwen3 Reasoning Configuration

Qwen3 supports a reasoning or "thinking" mode. This was unnecessary for the intended application because the deterministic software layer will already have performed the relevant calculations and supplied verified results.

Reasoning was therefore disabled at server level:

```text
--reasoning off
```

This prevents the client application from having to know that reasoning must be disabled and makes non-reasoning behaviour a property of the FarmPi LLM service.

Testing also identified that an earlier `enable_thinking=false` chat-template option had been deprecated by the installed `llama.cpp` version.

## Measured Qwen3 1.7B Performance

Detailed server timing produced approximately:

```text
Prompt processing: 7–8 tokens/second
Text generation:    approximately 2.5 tokens/second
```

One recorded transaction showed approximately 626 prompt tokens, 75.1 seconds prompt evaluation, 2.65 generated tokens/second, and 80.8 seconds total. Later requests benefited from prompt/context reuse, but generation remained about 2.5 tokens/second.

### Finding

Qwen3 1.7B operates successfully on the Raspberry Pi 4, but its performance is too slow for the intended conversational user experience. The limitation is CPU performance rather than RAM, storage, networking, power supply, or temperature.

## Smaller Model Test – Qwen3 0.6B

A second test used Qwen3 0.6B Q4_K_M, reasoning disabled, 2048-token context and one inference slot. Resident memory was about 796 MB and CPU remained close to fully used.

Representative generation results were approximately 6.8–7.2 tokens/second, materially faster than the 1.7B model. This made short deterministic-result responses more usable.

Approximate comparison:

| Model | Prompt Processing | Generation | Approx. RAM |
|---|---:|---:|---:|
| Qwen3 1.7B Q4_K_M | 7–8 t/s | ~2.5 t/s | ~1.5 GB |
| Qwen3 0.6B Q4_K_M | 22–25 t/s | ~7 t/s | ~0.8 GB |

## Historical interpretation

At this stage, Qwen3 0.6B appeared potentially usable if its role remained tightly constrained. The original design assumed deterministic software would perform all factual/analytical work and the model would primarily understand a narrow question and phrase a supplied result.

That hypothesis was valuable for proving the local Pi chain but was later revised by the 27 August learner-language findings above. The Pi measurements remain valid; the assumption that the learner-facing model could stay equally narrow does not.

## Application-Layer Testing

A Python web application was introduced between the client and the LLM so users could ask ordinary questions without seeing system prompts or raw database operations. This became the basis for the later MariaDB grounding, analytics, semantic interpretation and Flexible Learning architecture.

Voice input and output occur on the Android device rather than on the Raspberry Pi. The phone performs speech-to-text, sends text to FarmPi, receives a text response, and uses device text-to-speech for playback.

## Current Raspberry Pi 4 Assessment

The Raspberry Pi 4 successfully demonstrates local LLM hosting and remains the FarmPi application/database platform.

For inference, the current position is deliberately experimental:

- Qwen3 0.6B is fast enough for very short constrained responses but has shown learner-language brittleness;
- Qwen3 1.7B is linguistically worth re-testing but is slow on the Pi 4 at roughly 2.5 generated tokens/second;
- Qwen3.5-9B on the development PC is the current reference model used to separate architecture quality from small-model limitations.

No final deployment-model decision should be made until the new conversational test suite can be run consistently against each candidate.

## Alternative Hardware Considered

Raspberry Pi 5, RK3588 systems and NVIDIA Jetson Orin Nano remain possible future inference platforms. The main capstone objective is not embedded accelerator engineering, so hardware decisions should follow measured learner-experience requirements rather than drive the project prematurely.

## Current conclusion

Testing has demonstrated that:

1. an 8 GB Raspberry Pi 4 can run local Qwen models and the complete FarmPi application chain;
2. Pi 4 inference is CPU-limited rather than RAM-limited for the models tested;
3. Qwen3 0.6B is much faster than 1.7B on the Pi but is more brittle for open learner language;
4. Qwen3 1.7B remains worth controlled re-evaluation once the architecture is stable;
5. Qwen3.5-9B on the RTX 3070 development PC provides a useful reference-quality language layer at roughly 24 generated tokens/second;
6. deterministic software should still calculate FarmPi facts and control state-changing actions;
7. the language layer now has a broader responsibility for semantic interpretation and agricultural teaching;
8. the final model should be selected by a repeatable learner-conversation benchmark, not generation speed alone.

## Next testing

The next comparison should run the same conversation suite against the reference model and Pi-hosted candidates. Useful measures include:

- semantic interpretation success across paraphrases;
- polite/indirect command handling;
- speech-recognition variant recovery;
- factual grounding correctness;
- broad agricultural explanation quality;
- source/provenance discipline;
- clarification quality when confidence is low;
- time to first useful answer;
- total response time;
- generated tokens/second.

The goal is to find the smallest model that preserves the Flexible Learning experience after the architecture itself is working correctly.
