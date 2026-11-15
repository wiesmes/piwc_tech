# EcoSort website and Pico hardware

EcoSort accepts image uploads, passes recognition output through Pennsylvania disposal guidance, and can send bin commands to a Raspberry Pi Pico. The browser UI is served locally by FastAPI. Recognition currently uses an explicitly labeled mock provider; hardware can use either the mock adapter or real USB serial. Real hardware mode never silently falls back to mock.

## Run locally on Windows

Connect the Pico by USB and close Thonny or any other program using its serial port. From PowerShell in the repository root:

```powershell
python -m pip install -r requirements.txt
$env:ECOSORT_RECOGNITION_PROVIDER = "mock"
$env:ECOSORT_HARDWARE_MODE = "serial"
$env:ECOSORT_SERIAL_PORT = "COM6"
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --log-level info
```

Change COM6 if Device Manager shows a different port. Open http://127.0.0.1:8000. The backend opens the serial connection at startup and closes it at shutdown. Failed connections and disconnects are reported in `/api/status`; manual commands report communication errors rather than simulated success. Restart the backend after reconnecting the Pico; automatic reconnection is not implemented. Use one server worker so only one process owns the serial port.

To run without a Pico, select mock hardware explicitly:

```powershell
$env:ECOSORT_HARDWARE_MODE = "mock"
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

In mock mode, status reports MOCK and disconnected. Simulated acknowledgments do not indicate physical LED activity. Recognition is mocked independently of hardware: connecting a real Pico does not enable real image recognition. Unsupported recognition provider settings fail at startup rather than mislabeling mock results. The experimental CLIP classifier and its optional `requirements-ai.txt` dependencies are not yet connected as an API provider.

## Backend and frontend contract

- `GET /api/status` reports truthful hardware connection/mode/error, camera availability, recognition provider, location, and demo mode.
- `GET /api/events` returns queued button events as `{"events":["EVT BUTTON"]}` and drains those returned events. Mock mode returns an empty list.
- `POST /api/command` accepts JSON `command`: `RECYCLE`, `COMPOST`, `LANDFILL`, `UNKNOWN`, or `OFF`.
- `POST /api/classify` accepts multipart `photo` and an optional mock-only item-name `hint`. JPG, PNG, and WEBP uploads up to 10 MB are accepted. A hint identifies an item; the rules adapter chooses the bin.

Classification passes recognition output through `rules.p2_adapter.process_recognition`. The response includes `recognition`, `recommendation`, per-item `objects`, `object_count`, `multiple_items`, command replies/errors, and explicit mock flags. Multi-item images receive separate recommendations and no collective hardware command. The frontend displays material, explanation, clarification, and source/date metadata when available.

Pennsylvania statewide guidance is not verified Princeton campus guidance and does not establish a local collection bin. Without a verified local program, safe results may be UNKNOWN. Demo rules are disabled by default; use `ECOSORT_LOCATION=DEMO_ONLY` and `ECOSORT_DEMO_MODE=true` only for a labeled demonstration.

LCD support remains disabled (`LCD_ENABLED = False` in `pico/main.py`). Classification retains the protocol's `TEXT` command and acknowledgment, but the disabled firmware does not drive an LCD. Manual controls operate the LEDs.

## Verify physical button receipt

1. Start in serial mode and confirm `/api/status` reports connected hardware. Test all five manual LED controls and check their acknowledgments.
2. Press the physical button. The single serial reader logs `Received Pico event: EVT BUTTON` at INFO level and queues it separately from command replies. No second reader is used.
3. The frontend polls `/api/events` every 500 ms. Its PHYSICAL BUTTON indicator shows "Physical button pressed", a count, and the browser's last-received time. The count belongs to that page session, and the time is display receipt time, not a firmware timestamp.
4. To inspect the raw backend event, close the page first, press the button, then run `Invoke-RestMethod http://127.0.0.1:8000/api/events`. The next request returns an empty list. A browser tab or another consumer can drain the event first; this is a bounded queue, not a broadcast stream.

There is no backend camera capture or physical-button-to-classification pipeline yet. EVT BUTTON updates the indicator only; it does not pretend a scan occurred. The UI reports "Camera unavailable" and accepts uploaded photos. Connecting a camera, capturing an image on the button event, wiring a real recognition provider, and delivering its results to the UI remain integration work.

## Tests

```powershell
python -m pytest
```

API tests require the HTTP client dependency expected by the installed Starlette TestClient (this environment requests `httpx2`; other versions use `httpx`) in addition to the application dependencies. Serial tests use a fake port and do not establish that a physical Pico or camera works.
