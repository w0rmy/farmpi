# Raspberry Pi 4 Local LLM Testing – Preliminary Findings

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

One recorded transaction showed:

```text
626 prompt tokens
Prompt evaluation: 75.1 seconds
Generation rate:   2.65 tokens/second
Total time:        80.8 seconds
```

Later requests benefited from prompt/context reuse, reducing prompt-processing time substantially, but text generation remained approximately:

```text
2.5 tokens/second
```

At this rate, a 100-token response requires approximately 40 seconds of generation time alone.

### Finding

Qwen3 1.7B operates successfully on the Raspberry Pi 4, but its performance is too slow for the intended conversational user experience.

The limitation is CPU performance rather than RAM, storage, networking, power supply, or temperature.

## Smaller Model Test – Qwen3 0.6B

A second test was performed using:

- Qwen3 0.6B
- Q4_K_M quantisation
- reasoning disabled
- 2048-token context
- a single inference slot using `--parallel 1`

The smaller model reduced memory utilisation substantially:

```text
Resident memory: approximately 796 MB
RAM utilisation: approximately 10%
```

The CPU was still heavily utilised:

```text
llama-server: approximately 375% CPU
```

This was expected because `llama.cpp` continues to make use of all available CPU cores. The significant difference was how much work could be completed with that CPU capacity.

### Measured Qwen3 0.6B Performance

One representative request produced:

```text
Prompt tokens:       222
Prompt processing:   25.24 tokens/second
Generated tokens:    105
Generation speed:    7.21 tokens/second
Total request time:  23.23 seconds
```

A later, much shorter response produced:

```text
Prompt tokens:       132
Prompt processing:   22.50 tokens/second
Generated tokens:    8
Generation speed:    6.83 tokens/second
Total request time:  6.89 seconds
```

The model correctly returned the requested deterministic result:

```text
Paddock A is driest.
```

This is a substantial improvement over the 1.7B model.

Approximate comparison:

| Model | Prompt Processing | Generation | Approx. RAM |
|---|---:|---:|---:|
| Qwen3 1.7B Q4_K_M | 7–8 t/s | ~2.5 t/s | ~1.5 GB |
| Qwen3 0.6B Q4_K_M | 22–25 t/s | ~7 t/s | ~0.8 GB |

## Interpretation

The Qwen3 0.6B results demonstrate that model size has a major effect on practical usability on the Raspberry Pi 4.

The smaller model may be usable if its role remains tightly constrained.

The intended architecture does not require the LLM to:

- analyse raw sensor datasets;
- determine minima, maxima, averages or trends;
- generate statistical conclusions;
- independently establish factual results;
- act as a general-purpose farming expert.

Instead, deterministic software can perform these functions and provide the LLM with compact verified information such as:

```text
Driest paddock: Paddock A
Soil moisture: 18%
Farm average: 23%
```

The LLM then only needs to understand the user's question and turn the supplied result into appropriate natural language.

This significantly reduces the capability required from the model and makes a small model more realistic.

## Application-Layer Testing

A small Python web application was subsequently introduced between the phone and `llama-server`.

The intended architecture is:

```text
Android phone / browser
        ↓
Python FarmPi application
        ↓
Deterministic farm data/results
        ↓
System instructions
        ↓
Qwen3 0.6B / llama-server
        ↓
Natural-language response
        ↓
Android phone
```

The user therefore only needs to ask a normal question such as:

```text
Which paddock is driest?
```

The application automatically adds:

- system instructions;
- behavioural constraints;
- verified farm data;
- deterministic results;
- later, user interaction-profile information.

This removes the requirement for users to understand prompting.

Text-based interaction through this application has been successfully demonstrated.

Voice input and output are intended to occur on the Android device rather than on the Raspberry Pi. The phone performs speech-to-text, transmits text to FarmPi, receives a textual response, and uses the phone's own text-to-speech capability to speak the answer.

HTTPS will be required for the browser-based speech interface because browser microphone APIs require an appropriate secure context.

## Current Raspberry Pi 4 Assessment

The Raspberry Pi 4 has successfully demonstrated that a local LLM can operate as part of the proposed architecture.

However, testing has identified a significant performance constraint.

### Qwen3 1.7B

**Not considered suitable** for the intended interactive application.

Although the model operates correctly, approximately 2.5 generated tokens per second and near-total CPU utilisation produce unacceptable response latency.

### Qwen3 0.6B

**Potentially suitable for continued prototyping**, provided that:

- responses remain short;
- deterministic software performs all analytical work;
- prompts remain compact;
- static prompt context is reused where possible;
- the LLM is limited to language interpretation and explanation;
- testing confirms that the smaller model follows instructions reliably enough.

The approximately 7-token-per-second generation rate is materially more usable, particularly when typical responses may only contain 10–30 generated tokens.

The Raspberry Pi 4 should therefore not yet be completely rejected, but it appears to be operating close to the lower performance boundary for this application.

## Alternative Hardware Considered

### Raspberry Pi 5

A Raspberry Pi 5 would provide considerably greater CPU performance than the Pi 4 and could potentially improve CPU-based LLM inference.

A Raspberry Pi 5 combined with suitable AI-acceleration hardware may also provide another possible approach.

However, once the cost of a Pi 5 and an appropriate AI accelerator is considered, the total system cost begins to approach more purpose-built AI platforms.

This makes the cost/performance trade-off important.

### Orange Pi / RK3588

RK3588-based systems were investigated because they include an integrated NPU capable of accelerating neural-network inference.

Although potentially attractive in cost and performance, use of the NPU involves additional Rockchip-specific tooling, model conversion, runtimes and integration work.

This was rejected as a preferred direction because the capstone is intended to investigate AI-supported data access and flexible learning, rather than become an embedded AI engineering project.

### NVIDIA Jetson Orin Nano

The NVIDIA Jetson Orin Nano represents a technically attractive platform because it combines:

- ARM Linux;
- Ubuntu/Jetson Linux;
- Python;
- MariaDB;
- standard Linux networking;
- NVIDIA CUDA/GPU acceleration;
- local LLM inference;
- USB/SPI connectivity suitable for LoRa or LoRaWAN gateways.

It would allow the farm-data application, database, deterministic analytics, web/API layer and GPU-accelerated LLM inference to operate on one platform.

From a technical and development perspective, it appears substantially easier to integrate than an RK3588/NPU solution.

The major limitation is cost. Current pricing makes the Jetson difficult to justify purely as an experimental capstone platform.

It is therefore considered an **ideal technical option but currently an expensive prototype option**.

## Preliminary Conclusion

Testing has demonstrated that:

1. A local LLM can successfully run on an 8 GB Raspberry Pi 4.
2. The Raspberry Pi 4 has sufficient RAM for the lightweight models tested.
3. Power and thermal issues can be eliminated and are not the primary bottleneck.
4. Qwen3 1.7B is too slow for the required conversational interface, generating approximately 2.5 tokens per second.
5. Qwen3 0.6B performs substantially better, generating approximately 7 tokens per second.
6. The smaller model may remain viable if it is used only as a constrained language interface over verified deterministic results.
7. Further optimisation should focus on compact prompts, context reuse, short responses and strict separation between deterministic analysis and language generation.
8. If the smaller model proves insufficient in quality or responsiveness, a more capable hardware platform will be required.
9. A Jetson Orin Nano currently appears to provide the cleanest technical path to local accelerated inference, although its cost may be excessive for the prototype.
10. The Raspberry Pi 4 remains worthwhile for continued experimentation before additional hardware expenditure is justified.

## Next Testing

The next stage should test whether Qwen3 0.6B is sufficiently reliable for the actual restricted task rather than assessing it as a general-purpose LLM.

Testing should concentrate on whether it can reliably:

- answer direct questions from verified results;
- avoid introducing unsupported information;
- state when information is unavailable;
- explain the same verified result at different levels of complexity;
- work with concise structured data;
- operate through the Python application layer;
- maintain acceptable latency with short real-world responses.

If these tests are successful, the Raspberry Pi 4 may remain adequate for the capstone prototype despite its limited general-purpose LLM performance.
