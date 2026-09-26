# Raspberry Pi backend validation - 26 September 2026

## Environment

- Host: deployed FarmPi Raspberry Pi
- Working directory: `~/farmpi`
- Python: 3.13 virtual environment under `./.venv`
- Validation target: current deployed FarmPi backend test suite

## Result

```text
Ran 146 tests in 1.291s

OK
```

All 146 tests passed.

## Expected diagnostic observed

```text
FarmPi semantic interpretation failed; using fast-route fallback: Semantic interpreter did not return a JSON object.
```

The suite still passed, so this output is recorded as exercised fallback behaviour rather than a test failure.

## Non-failing maintenance warnings

### Python sqlite3 datetime adapter

```text
DeprecationWarning: The default datetime adapter is deprecated as of Python 3.12
```

This warning was emitted from `tests/test_node_management.py` and relates to the SQLite test adapter. The production FarmPi database remains MariaDB.

### HTTP 422 status constant

```text
StarletteDeprecationWarning: 'HTTP_422_UNPROCESSABLE_ENTITY' is deprecated. Use 'HTTP_422_UNPROCESSABLE_CONTENT' instead.
```

The repository still references the older constant in `app/ingest_api.py`. This does not affect the passing result but should be updated as routine maintenance.

## Evidence interpretation

This run demonstrates that the current FarmPi backend, including managed-node behaviour, passes its automated validation suite directly on the deployed Raspberry Pi. It does not by itself prove Android device acceptance, physical sensor acquisition, MariaDB migration idempotence, or the final T01 six-sensor physical acceptance path.