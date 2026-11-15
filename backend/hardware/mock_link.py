class MockSerialAdapter:
    is_mock = True

    def send(self, command):
        if command in {"RECYCLE", "COMPOST", "LANDFILL", "UNKNOWN", "OFF"}:
            return f"OK {command}"
        if command.startswith("TEXT ") and 1 <= len(command[5:]) <= 16:
            return "OK TEXT"
        return "ERR INVALID_COMMAND"
