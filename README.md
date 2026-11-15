# EcoSort website and Pico hardware

The website can run with simulated hardware or send commands to a Raspberry Pi
Pico over USB serial. Hardware mode is selected explicitly; real mode does not
silently fall back to the mock adapter. The image scanner accepts a photo
uploaded or captured by the browser and uses the configured recognition
provider. A Pi camera is not connected to this backend.

## Windows: start with the Pico on COM6

Connect the Pico by USB and close Thonny or any other program using its serial
port. From PowerShell in the project directory:

```powershell
python -m pip install -r requirements.txt
$env:ECOSORT_HARDWARE_MODE = "serial"
$env:ECOSORT_SERIAL_PORT = "COM6"
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Change `COM6` if Device Manager shows a different port. The backend reports a
failed or disconnected Pico in `/api/status` and command requests return an
error; it does not switch to simulated hardware. Use `Ctrl+C` to stop the
server and close the serial connection.

Open [http://127.0.0.1:8000](http://127.0.0.1:8000). Check the hardware status
shows `CONNECTED`, then use the Recycle, Compost, Landfill, Unknown, and Turn
off manual controls to test the LEDs. Their commands are sent to the Pico and
the website shows the corresponding acknowledgment or communication error.

To run without the Pico, select mock mode explicitly:

```powershell
$env:ECOSORT_HARDWARE_MODE = "mock"
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

In serial mode, `GET /api/events` returns queued button events such as
`{"events":["EVT BUTTON"]}` and clears the returned events. The serial reader
also ignores empty lines and lines beginning with `#`. Upload-based
classification and the existing mock recognition provider are unchanged.