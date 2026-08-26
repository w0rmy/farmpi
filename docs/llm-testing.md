# Raspberry Pi 4 local LLM testing: preliminary findings

## Purpose

This testing assessed whether the existing Raspberry Pi 4 could run a local large language model (LLM) as part of the FarmPi monitoring project. The LLM is intended to provide a natural-language interface to verified results from the application; deterministic software remains responsible for retrieving sensor data and performing calculations.

The key question was whether the Pi could run a capable enough model quickly enough for an interactive interface.

## Test platform

- Raspberry Pi 4 with 8 GB RAM
- Raspberry Pi OS Lite 64-bit (Debian Trixie base)
- Headless operation on the local network
- `llama.cpp` and `llama-server`
- Android phone as the browser client
- Approximately 7.6 GiB usable RAM and a 2 GiB swap file

## Model tested

The initial substantial model was Qwen3 1.7B Instruct, in GGUF format using Q4_K_M quantisation and a 2,048-token context window.

The model loaded successfully and the `llama-server` web interface was reachable from the Android client. This proves that an 8 GB Raspberry Pi 4 can technically host and serve a small local LLM.

## Resource use observed

During generation, `llama-server` used approximately:

- 377–397% CPU, effectively saturating all four Pi 4 CPU cores
- 1.5 GB resident memory, about 20% of system RAM
- No swap

## Finding

Although the model ran, its CPU demand leaves very little headroom for sensor collection, storage, the web service, and normal operating-system work. The Pi 4 is therefore not considered a practical production platform for an interactive local LLM in this project. It remains suitable for the FarmPi application, data collection, and acting as a lightweight service host.

## Recommended direction

A Raspberry Pi 5 with an AI accelerator may improve performance, but it adds cost and integration complexity without guaranteeing that a capable LLM will feel responsive. A Jetson-class device is the more appropriate next platform to evaluate if local model inference is a firm project requirement, because its GPU-oriented architecture is better suited to this workload.

The next evaluation should compare response speed, sustained resource use, power consumption, and the ability to operate alongside the monitoring stack.
