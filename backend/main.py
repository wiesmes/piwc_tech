from pathlib import Path
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from backend.ecosort_api import create_ecosort_router
from backend.hardware.mock_link import MockSerialAdapter
from backend.recognition.mock_provider import MockProvider
from backend.config import Settings
from rules.engine import recommend

settings = Settings()
hardware = MockSerialAdapter()
recognizer = MockProvider()
app = FastAPI(title='EcoSort Mock Demo')

@app.get('/api/status')
def status():
    return {
        'hardware': {'connected': False, 'mock': True},
        'hardware_connected': False,
        'hardware_mode': 'mock',
        'recognition_provider': settings.recognition_provider,
        'location': settings.location,
    }

app.include_router(create_ecosort_router(settings, hardware, recognizer, recommend))
app.mount('/', StaticFiles(directory=str(Path(__file__).resolve().parents[1] / 'frontend'), html=True), name='frontend')
