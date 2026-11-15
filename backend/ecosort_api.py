"""EcoSort API routes to integrate into the existing FastAPI starter.

Usage in backend/main.py, BEFORE the frontend static mount:

    from backend.ecosort_api import create_ecosort_router
    app.include_router(create_ecosort_router(settings, hardware, recognizer))

Recognition results pass through the Pennsylvania rules adapter before hardware dispatch.
"""
from __future__ import annotations

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from rules.p2_adapter import process_recognition

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


def create_ecosort_router(settings, hardware, recognizer):
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
        try:
            decision = process_recognition(
                recognition,
                location=settings.location,
                demo_mode=settings.demo_mode,
            )
        except Exception as error:
            raise HTTPException(status_code=500, detail=f"Rule evaluation failed: {error}") from error

        objects = decision.get("objects", [])
        if not isinstance(objects, list):
            objects = []
        for result in objects:
            if isinstance(result, dict):
                result["demo"] = (
                    str(result.get("rule_id") or "").startswith("DEMO_")
                    or str(result.get("message") or "").startswith("DEMO ONLY")
                )
        is_multi = decision.get("multiple_items") is True
        if is_multi:
            recommendation = {
                "bin": "UNKNOWN",
                "message": decision.get("message", "Select an item before sorting."),
                "needs_clarification": True,
            }
        elif objects:
            recommendation = dict(objects[0])
        else:
            recommendation = {
                "bin": "UNKNOWN",
                "message": decision.get("message", "No usable disposal recommendation is available."),
                "needs_clarification": True,
            }
        recommendation["demo"] = (
            str(recommendation.get("rule_id") or "").startswith("DEMO_")
            or str(recommendation.get("message") or "").startswith("DEMO ONLY")
        )

        commands_sent = []
        pico_replies = []
        hardware_error = None
        if not is_multi:
            # Never send one collective bin when several items were detected.
            item = recommendation.get("item") or recognition.get("item")
            bin_name = recommendation.get("bin")
            if bin_name not in VALID_BINS:
                bin_name = "UNKNOWN"
            try:
                commands_sent.append(bin_name)
                pico_replies.append(send_ack(hardware, bin_name))
                text_command = "TEXT " + lcd_label(item)
                commands_sent.append(text_command)
                pico_replies.append(send_ack(hardware, text_command))
            except Exception as error:
                hardware_error = str(error)
        return {
            "recognition": recognition, "recommendation": recommendation,
            "objects": objects,
            "object_count": decision.get("object_count", len(objects)),
            "multiple_items": is_multi,
            "commands_sent": commands_sent, "pico_replies": pico_replies,
            "mock_recognition": str(settings.recognition_provider).lower() == "mock",
            "mock_hardware": bool(hardware.is_mock), "hardware_error": hardware_error,
        }

    return router
