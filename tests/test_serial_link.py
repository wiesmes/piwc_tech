import logging
import queue

import pytest

from backend.hardware.serial_link import (
    SerialConnectionError,
    SerialHardwareAdapter,
    SerialProtocolError,
    SerialTimeoutError,
)


class FakeSerial:
    def __init__(self, respond=True, **_kwargs):
        self.lines = queue.Queue()
        self.respond = respond
        self.writes = []
        self.closed = False

    def write(self, payload):
        self.writes.append(payload)
        if self.respond:
            command = payload.decode("ascii").strip()
            if command == "TEXT hello":
                self.lines.put(b"# debug line\r\n")
                self.lines.put(b"\r\n")
                self.lines.put(b"EVT BUTTON\r\n")
                self.lines.put(b"OK TEXT\r\n")
            else:
                self.lines.put(("OK " + command + "\r\n").encode("ascii"))
        return len(payload)

    def readline(self):
        try:
            return self.lines.get(timeout=0.02)
        except queue.Empty:
            return b""

    def close(self):
        self.closed = True


def test_send_uses_newline_and_reader_queues_button_events(caplog):
    fake_serial = FakeSerial()
    adapter = SerialHardwareAdapter(serial_factory=lambda **_kwargs: fake_serial)
    adapter.open()
    try:
        with caplog.at_level(logging.INFO, logger="backend.hardware.serial_link"):
            assert adapter.send("TEXT hello") == "OK TEXT"
        assert fake_serial.writes == [b"TEXT hello\n"]
        assert adapter.get_button_events() == ["EVT BUTTON"]
        assert adapter.get_button_events() == []
        assert "Received Pico event: EVT BUTTON" in caplog.text
    finally:
        adapter.close()

    assert fake_serial.closed
    assert adapter.is_mock is False
    assert adapter.is_connected is False


def test_send_times_out_without_acknowledgment():
    adapter = SerialHardwareAdapter(
        timeout=0.05,
        serial_factory=lambda **_kwargs: FakeSerial(respond=False),
    )
    adapter.open()
    try:
        with pytest.raises(SerialTimeoutError, match="Timed out"):
            adapter.send("OFF")
    finally:
        adapter.close()


def test_send_rejects_mismatched_acknowledgment():
    class WrongReplySerial(FakeSerial):
        def write(self, payload):
            self.writes.append(payload)
            self.lines.put(b"OK COMPOST\n")
            return len(payload)

    adapter = SerialHardwareAdapter(
        serial_factory=lambda **_kwargs: WrongReplySerial()
    )
    adapter.open()
    try:
        with pytest.raises(SerialProtocolError, match="Expected 'OK RECYCLE'"):
            adapter.send("RECYCLE")
    finally:
        adapter.close()


def test_send_fails_after_connection_closes():
    adapter = SerialHardwareAdapter(serial_factory=lambda **_kwargs: FakeSerial())
    adapter.open()
    adapter.close()

    with pytest.raises(SerialConnectionError, match="not connected"):
        adapter.send("OFF")


def test_button_event_route_returns_and_drains_queued_events(monkeypatch):
    from backend import main

    class EventHardware:
        is_mock = False

        def __init__(self):
            self.events = ["EVT BUTTON"]

        def get_button_events(self):
            events, self.events = self.events, []
            return events

    monkeypatch.setattr(main, "hardware", EventHardware())

    assert main.button_events() == {"events": ["EVT BUTTON"]}
    assert main.button_events() == {"events": []}