import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from backend.ecosort_api import create_ecosort_router
from backend.hardware.mock_link import MockSerialAdapter
from backend.hardware.serial_link import SerialConnectionError, SerialHardwareAdapter
from backend.recognition.mock_provider import MockProvider
from backend.config import Settings
from rules.engine import recommend

settings = Settings()
hardware_mode = os.environ.get("ECOSORT_HARDWARE_MODE", "mock").strip().lower()
if hardware_mode == "mock":
    hardware = MockSerialAdapter()
elif hardware_mode == "serial":
    serial_port = os.environ.get("ECOSORT_SERIAL_PORT", "COM6").strip()
    if not serial_port:
        raise ValueError("ECOSORT_SERIAL_PORT must not be empty in serial mode")
    hardware = SerialHardwareAdapter(port=serial_port)
else:
    raise ValueError(
        "ECOSORT_HARDWARE_MODE must be either 'mock' or 'serial', "
        f"not {hardware_mode!r}"
    )

recognizer = MockProvider()


@asynccontextmanager
async def lifespan(_app):
    if not hardware.is_mock:
        try:
            hardware.open()
        except SerialConnectionError as error:
            logging.getLogger(__name__).error("Pico hardware unavailable: %s", error)
    try:
        yield
    finally:
        if not hardware.is_mock:
            hardware.close()


app = FastAPI(title="EcoSort", lifespan=lifespan)

@app.get('/api/status')
def status():
    connected = not hardware.is_mock and hardware.is_connected
    return {
        'hardware': {
            'connected': connected,
            'mock': hardware.is_mock,
            **({"port": hardware.port} if not hardware.is_mock else {}),
        },
        'hardware_connected': connected,
        'hardware_mode': 'mock' if hardware.is_mock else 'serial',
        'hardware_error': None if hardware.is_mock else hardware.last_error,
        'camera_connected': False,
        'recognition_provider': settings.recognition_provider,
        'location': settings.location,
    }


@app.get("/api/events")
def button_events():
    events = [] if hardware.is_mock else hardware.get_button_events()
    return {"events": events}


app.include_router(create_ecosort_router(settings, hardware, recognizer, recommend))
app.mount('/', StaticFiles(directory=str(Path(__file__).resolve().parents[1] / 'frontend'), html=True), name='frontend')
