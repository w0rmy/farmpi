# Historical local-LLM evaluation

This record preserves measured implementation evidence without presenting earlier model choices as the current FarmPi architecture. Model selection is a deployment constraint and optimisation variable; the capstone focus is the embedded learning platform.

## Raspberry Pi 4 experiments

An 8 GB Raspberry Pi 4 successfully ran the complete FarmPi application chain, MariaDB, Caddy, `llama.cpp`, and quantised Qwen models. CPU inference, rather than memory, storage, network, power, or temperature, was the dominant limit.

| Model/configuration | Prompt processing | Generation | Approx. resident memory | Interpretation |
|---|---:|---:|---:|---|
| Qwen3 1.7B Q4_K_M, context 2048, one slot, reasoning off | 7-8 tokens/s | about 2.5 tokens/s | about 1.5 GB | Functioned, but conversational generation was slow on Pi 4. |
| Qwen3 0.6B Q4_K_M, context 2048, one slot, reasoning off | 22-25 tokens/s | about 6.8-7.2 tokens/s | about 0.8 GB | Faster for short supplied-result phrasing, but more brittle with natural learner language. |

The 1.7B test produced a representative response in roughly 80.8 seconds before later prompt and routing optimisations. The 0.6B test produced a concise representative response in roughly 6.9 seconds. These are observations from a particular prototype, not portable performance promises.

## Optimisations retained as design lessons

- answer deterministic requests directly where generated phrasing adds no learning value;
- supply only the bounded facts and source context needed for the request;
- keep prompts and visible responses concise;
- reuse the HTTP connection to the model server;
- expose stage timings so database, routing, model, and total latency can be separated;
- disable hidden reasoning when it consumes the response budget without improving the learner-visible answer.

These optimisations reduce waiting while preserving the authority boundary: the model does not query MariaDB, calculate farm results, invent readings, resolve database identity, or authorise mutations.

## Development/reference model

Later evaluation used Qwen3.5-9B Q4_K_M hosted by LM Studio on a Windows development PC with an RTX 3070. With reasoning disabled, observed generation was approximately 24 tokens/s. This reference setup helped distinguish architecture and prompt quality from small-model limitations. It is not required by the checked-in Raspberry Pi deployment, which currently configures Qwen3 1.7B through `llama-server`.

`app/llm_compat.py` combines FarmPi's system prompt fragments for stricter chat templates and can apply the configured model identifier. This permits the same grounding and routing design to be evaluated against either topology.

## Current conclusion

The Pi can host a useful local model, but no model size is treated as the capstone claim. Keep the deterministic farm-data boundary and open, source-aware learning behaviour stable; then evaluate model/hardware combinations for language quality, latency, privacy, cost, and operational simplicity.
