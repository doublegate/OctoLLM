# Reflex layer contract fixtures

Captured from a **running reflex layer**, not hand-written.

The orchestrator's 39 reflex-client tests all mocked `httpx` with dicts the Python
models already agreed with, so they passed while the real integration could not
succeed for any input at all: the Rust service emitted `status: "success"` where the
client's enum required `"Success"`, and `start`/`end`/`matched_text` where the client
required `position`/`value`/`context`. Mocks written from the client's own shape can
only ever confirm the client agrees with itself.

Regenerate after any change to the reflex wire format:

```sh
make redis
cargo run -p reflex-layer --bin reflex-layer &      # REFLEX_SERVER__PORT=18080
python scripts/capture_reflex_fixtures.py
```

`request_id` and `processing_time_ms` are normalised to fixed values so the fixtures
are stable; everything else is exactly what the service sent.
