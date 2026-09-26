# ESP32-S3 physical node configuration bring-up

Both boards run this same sketch. It registers, pulls and validates complete
configuration, persists it in NVS and acknowledges the applied SHA-256 fingerprint.
It contains no physical driver and sends no invented readings.

See [setup, contract and hardware evidence checklist](../../docs/s3-node-bringup.md).
The existing `../esp32-sensor` sketch remains an explicitly simulated evaluation
generator. `board_profile.h` owns physical-board decisions; GPIOs are intentionally
unset until the carrier board and probe are identified.
