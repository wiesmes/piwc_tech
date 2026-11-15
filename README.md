# EcoSort

EcoSort identifies waste items, checks them against Pennsylvania disposal guidance, and can send a bin command to a Raspberry Pi Pico. The browser UI is served locally by FastAPI; the current default recognition and hardware adapters are explicitly mocked.

## Run locally

Install the lightweight application dependencies, then start the server from the repository root:

```powershell
python -m pip install -r requirements.txt
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

Open `http://127.0.0.1:8000`. In the default mock mode, `/api/status` reports the Pico as disconnected and mock; simulated command acknowledgements do not mean physical LEDs were activated.

The scanner accepts JPG, PNG, and WEBP uploads up to 10 MB. The mock provider can take an optional item-name hint; a hint identifies an item only and never determines the disposal bin.

## Backend contract

- `GET /api/status` reports the hardware mode, recognition provider, location, and demo mode.
- `POST /api/command` accepts a JSON `command`: `RECYCLE`, `COMPOST`, `LANDFILL`, `UNKNOWN`, or `OFF`.
- `POST /api/classify` accepts multipart `photo` and an optional mock-only `hint`.

Classification passes recognition output through `rules.p2_adapter.process_recognition`. The rules adapter, not the recognition model, chooses a bin. It can return separate per-item results for multi-object images; the backend does not send one collective hardware command for them. The UI displays each item's material, decision, explanation, clarification question, and source/date metadata when available.

Pennsylvania statewide guidance alone does not establish a local collection bin. Without a verified local program, safe results may be `UNKNOWN`. Demo rules are disabled by default; enable them only for a labeled demonstration with `ECOSORT_LOCATION=DEMO_ONLY` and `ECOSORT_DEMO_MODE=true`.

## Tests

```powershell
python -m pytest
```