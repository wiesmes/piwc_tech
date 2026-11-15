"""EcoSort API routes to integrate into the existing FastAPI starter.

Usage in backend/main.py, BEFORE the frontend static mount:

    from backend.ecosort_api import create_ecosort_router
    from rules.engine import recommend
    app.include_router(create_ecosort_router(settings, hardware, recognizer, recommend))

Works with the existing settings / MockSerialAdapter / MockProvider contracts.
"""
from __future__ import annotations

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

VALID_BINS = {"RECYCLE", "COMPOST", "LANDFILL", "UNKNOWN"}
VALID_COMMANDS = VALID_BINS | {"OFF"}
MAX_UPLOAD_BYTES = 10 * 1024 * 1024

class CommandRequest(BaseModel):
    command: str


def as_dict(result):
    if isinstance(result, dict):
        return result
    if hasattr(result, "model_dump"):
        return result.model_dump()
    raise ValueError("Recognition provider must return a dictionary or Pydantic model")


def lcd_label(item):
    text = str(item or "Unknown item").encode("ascii", errors="ignore").decode("ascii")
    return (" ".join(text.split()) or "Unknown item")[:16]


def send_ack(hardware, command):
    """Reject ERR / timeout / nonmatching ACK; do not report success falsely."""
    reply = hardware.send(command)
    expected = "OK TEXT" if command.startswith("TEXT ") else f"OK {command}"
    if not isinstance(reply, str) or reply.strip() != expected:
        raise RuntimeError(f"Expected {expected!r}; got {reply!r}")
    return reply.strip()


def create_ecosort_router(settings, hardware, recognizer, recommend):
    router = APIRouter()

    @router.post("/api/command")
    def command_endpoint(payload: CommandRequest):
        command = payload.command.strip().upper()
        if command not in VALID_COMMANDS:
            raise HTTPException(status_code=400, detail="Invalid command. Use RECYCLE, COMPOST, LANDFILL, UNKNOWN or OFF.")
        try:
            reply = send_ack(hardware, command)
        except Exception as error:
            raise HTTPException(status_code=503, detail=f"Pico communication failed: {error}") from error
        return {"command": command, "reply": reply, "mock": bool(hardware.is_mock)}

    @router.post("/api/classify")
    async def classify_endpoint(photo: UploadFile = File(...), hint: str | None = Form(None)):
        # Read at most 10MB+1, instead of loading arbitrarily large uploads.
        image = await photo.read(MAX_UPLOAD_BYTES + 1)
        if not image:
            raise HTTPException(status_code=400, detail="Choose a nonempty photo.")
        if len(image) > MAX_UPLOAD_BYTES:
            raise HTTPException(status_code=413, detail="Maximum upload size is 10 MB.")
        # Validate common image magic bytes; HEIC/HEIF is explicitly rejected unless
        # the vision teammate adds and validates decoder support.
        recognized_header = (image.startswith(b'\xff\xd8\xff') or image.startswith(b'\x89PNG\r\n\x1a\n')
                            or (image.startswith(b'RIFF') and image[8:12] == b'WEBP'))
        if not recognized_header:
            raise HTTPException(status_code=415, detail="Unsupported image. Upload a JPG, PNG, or WEBP. Convert iPhone HEIC to JPG first.")
        use_hint = (hint or "").strip()[:100] if str(settings.recognition_provider).lower() == "mock" else None
        try:
            recognition = as_dict(recognizer.recognize(image, hint=use_hint))
        except Exception as error:
            raise HTTPException(status_code=502, detail=f"Recognition failed: {error}") from error
        if recognition.get("needs_clarification") or not recognition.get("item"):
            recommendation = {
                "bin": "UNKNOWN", "message": "Not enough information to safely recommend a disposal bin.",
                "rule_id": None, "source_url": None, "demo": False,
            }
        else:
            try:
                recommendation = as_dict(recommend(recognition["item"], settings.location))
            except Exception as error:
                raise HTTPException(status_code=500, detail=f"Rule evaluation failed: {error}") from error
        if recommendation.get("bin") not in VALID_BINS:
            recommendation = {
                "bin": "UNKNOWN", "message": "No validated local disposal rule could be applied.",
                "rule_id": None, "source_url": None, "demo": False,
            }
        bin_name = recommendation["bin"]
        commands_sent = []
        pico_replies = []
        hardware_error = None
        # Recognition and rules are returned even if the Pico has disconnected.
        try:
            commands_sent.append(bin_name)
            pico_replies.append(send_ack(hardware, bin_name))
            item_text = lcd_label(recognition.get("item"))
            text_command = "TEXT " + item_text
            commands_sent.append(text_command)
            pico_replies.append(send_ack(hardware, text_command))
        except Exception as error:
            hardware_error = str(error)
        return {
            "recognition": recognition, "recommendation": recommendation,
            "commands_sent": commands_sent, "pico_replies": pico_replies,
            "mock_recognition": str(settings.recognition_provider).lower() == "mock",
            "mock_hardware": bool(hardware.is_mock), "hardware_error": hardware_error,
        }

    return router
