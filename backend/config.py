import os
from dataclasses import dataclass

@dataclass
class Settings:
    recognition_provider: str = os.getenv('ECOSORT_RECOGNITION_PROVIDER', 'mock').strip().lower()
    location: str = os.getenv('ECOSORT_LOCATION', 'PA_STATEWIDE').strip().upper()
    demo_mode: bool = os.getenv('ECOSORT_DEMO_MODE', 'false').strip().lower() in {'1', 'true', 'yes'}
