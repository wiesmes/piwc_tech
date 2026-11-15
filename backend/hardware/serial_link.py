"""Threaded USB serial adapter for the Pico command protocol."""

import logging
import threading
import time
from collections import deque


class SerialLinkError(RuntimeError):
    """Base error for Pico serial communication failures."""


class SerialConnectionError(SerialLinkError):
    """The Pico serial connection is unavailable or disconnected."""


class SerialTimeoutError(SerialLinkError):
    """The Pico did not acknowledge a command before its deadline."""


class SerialProtocolError(SerialLinkError):
    """The Pico returned an unexpected response."""


class SerialHardwareAdapter:
    is_mock = False

    def __init__(
        self,
        port="COM6",
        baudrate=115200,
        timeout=1.0,
        serial_factory=None,
        read_timeout=0.1,
    ):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.read_timeout = read_timeout
        self._serial_factory = serial_factory
        self._serial = None
        self._reader = None
        self._stop_reader = threading.Event()
        self._condition = threading.Condition()
        self._send_lock = threading.Lock()
        self._replies = deque()
        self._button_events = deque(maxlen=100)
        self._connected = False
        self._last_error = None

    @property
    def is_connected(self):
        with self._condition:
            return self._connected

    @property
    def last_error(self):
        with self._condition:
            return self._last_error

    def open(self):
        with self._condition:
            if self._connected:
                return

        try:
            serial_factory = self._serial_factory
            if serial_factory is None:
                import serial

                serial_factory = serial.Serial
            connection = serial_factory(
                port=self.port,
                baudrate=self.baudrate,
                timeout=self.read_timeout,
                write_timeout=self.timeout,
            )
        except (ImportError, OSError, ValueError) as error:
            message = f"Could not open Pico on {self.port}: {error}"
            with self._condition:
                self._connected = False
                self._last_error = message
                self._condition.notify_all()
            raise SerialConnectionError(message) from error

        with self._condition:
            self._serial = connection
            self._last_error = None
            self._connected = True
            self._stop_reader.clear()
            self._reader = threading.Thread(
                target=self._read_responses,
                name="pico-serial-reader",
                daemon=True,
            )
            self._reader.start()

    def close(self):
        self._stop_reader.set()
        with self._condition:
            connection = self._serial
            reader = self._reader
            self._connected = False
            self._condition.notify_all()

        if connection is not None:
            try:
                connection.close()
            except OSError as error:
                with self._condition:
                    self._last_error = f"Error closing Pico serial port: {error}"

        if reader is not None and reader is not threading.current_thread():
            reader.join(timeout=max(1.0, self.read_timeout * 2))

        with self._condition:
            self._serial = None
            self._reader = None

    def get_button_events(self):
        with self._condition:
            events = list(self._button_events)
            self._button_events.clear()
            return events

    def send(self, command):
        expected = self._expected_reply(command)
        with self._send_lock:
            with self._condition:
                if not self._connected or self._serial is None:
                    detail = self._last_error or f"Pico is not connected on {self.port}"
                    raise SerialConnectionError(detail)
                connection = self._serial
                self._replies.clear()

            try:
                payload = (command + "\n").encode("ascii")
                written = connection.write(payload)
                if written != len(payload):
                    raise OSError(f"Incomplete write to Pico on {self.port}")
            except (OSError, UnicodeEncodeError) as error:
                message = f"Could not send command to Pico on {self.port}: {error}"
                self._mark_disconnected(message)
                raise SerialConnectionError(message) from error

            deadline = time.monotonic() + self.timeout
            with self._condition:
                while True:
                    if self._replies:
                        reply = self._replies.popleft()
                        if reply != expected:
                            raise SerialProtocolError(
                                f"Expected {expected!r}; got {reply!r}"
                            )
                        return reply

                    if not self._connected:
                        detail = self._last_error or "Pico serial connection was lost"
                        raise SerialConnectionError(detail)

                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        raise SerialTimeoutError(
                            f"Timed out waiting for {expected!r} from Pico"
                        )
                    self._condition.wait(remaining)

    @staticmethod
    def _expected_reply(command):
        if not isinstance(command, str) or not command.isascii():
            raise ValueError("Pico commands must be ASCII text")
        if "\n" in command or "\r" in command:
            raise ValueError("Pico commands must not contain line breaks")
        if command in {"RECYCLE", "COMPOST", "LANDFILL", "UNKNOWN", "OFF"}:
            return f"OK {command}"
        if command.startswith("TEXT ") and len(command[5:]) <= 16:
            return "OK TEXT"
        raise ValueError(f"Unsupported Pico command: {command!r}")

    def _read_responses(self):
        while not self._stop_reader.is_set():
            with self._condition:
                connection = self._serial
            if connection is None:
                return

            try:
                raw_line = connection.readline()
            except OSError as error:
                if not self._stop_reader.is_set():
                    self._mark_disconnected(
                        f"Pico serial connection lost on {self.port}: {error}"
                    )
                return

            if not raw_line:
                continue

            line = raw_line.decode("ascii", errors="replace").strip()
            if not line or line.startswith("#"):
                continue

            with self._condition:
                if line == "EVT BUTTON":
                    self._button_events.append(line)
                    logging.getLogger(__name__).info("Received Pico event: %s", line)
                else:
                    self._replies.append(line)
                self._condition.notify_all()

    def _mark_disconnected(self, message):
        with self._condition:
            self._connected = False
            self._last_error = message
            self._condition.notify_all()
