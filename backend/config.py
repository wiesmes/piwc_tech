from dataclasses import dataclass

@dataclass
class Settings:
    recognition_provider: str = 'mock'
    location: str = 'UNCONFIGURED'
