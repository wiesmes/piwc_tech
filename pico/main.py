"""USB serial controller for the original RP2040 Raspberry Pi Pico."""

import sys
import time
import uselect

from machine import Pin


GREEN_PIN = 14
YELLOW_PIN = 15
RED_PIN = 16
BUTTON_PIN = 17

# LCD support stays off until the exact module and I2C electrical levels are checked.
LCD_ENABLED = False
LCD_I2C_ADDRESS = None

DEBUG = False
MAX_LINE_LENGTH = 64
MAX_INPUT_CHARS_PER_LOOP = 64
BLINK_INTERVAL_MS = 500
DEBOUNCE_MS = 30


def debug(message):
    if DEBUG:
        sys.stdout.write("# " + str(message) + "\n")


def set_leds(leds, green, yellow, red):
    leds["green"].value(green)
    leds["yellow"].value(yellow)
    leds["red"].value(red)


def create_lcd():
    if not LCD_ENABLED:
        return None
    if LCD_I2C_ADDRESS is None:
        raise ValueError("Set LCD_I2C_ADDRESS after identifying the module")

    from machine import I2C
    from lcd_i2c import PCF8574LCD

    i2c = I2C(0, sda=Pin(0), scl=Pin(1), freq=100000)
    return PCF8574LCD(i2c, LCD_I2C_ADDRESS)


def set_lcd_line(lcd_state, line, text):
    lcd = lcd_state[0]
    if lcd is None:
        return
    try:
        lcd.write_line(line, text)
    except Exception as error:
        lcd_state[0] = None
        debug("LCD disabled after error: " + repr(error))


def send_reply(message):
    sys.stdout.write(message + "\n")


def handle_command(command, leds, lcd_state, state, now):
    if not command or any(ord(char) < 32 or ord(char) > 126 for char in command):
        return "ERR INVALID_COMMAND"

    if command == "RECYCLE":
        set_leds(leds, 1, 0, 0)
        state["mode"] = "STEADY"
        set_lcd_line(lcd_state, 1, "RECYCLE")
        set_lcd_line(lcd_state, 2, "")
        return "OK RECYCLE"

    if command == "COMPOST":
        set_leds(leds, 0, 1, 0)
        state["mode"] = "STEADY"
        set_lcd_line(lcd_state, 1, "COMPOST")
        set_lcd_line(lcd_state, 2, "")
        return "OK COMPOST"

    if command == "LANDFILL":
        set_leds(leds, 0, 0, 1)
        state["mode"] = "STEADY"
        set_lcd_line(lcd_state, 1, "LANDFILL")
        set_lcd_line(lcd_state, 2, "")
        return "OK LANDFILL"

    if command == "UNKNOWN":
        state["mode"] = "UNKNOWN"
        state["blink_on"] = True
        state["next_blink"] = time.ticks_add(now, BLINK_INTERVAL_MS)
        set_leds(leds, 1, 1, 1)
        set_lcd_line(lcd_state, 1, "CHECK PACKAGING")
        set_lcd_line(lcd_state, 2, "")
        return "OK UNKNOWN"

    if command == "OFF":
        state["mode"] = "OFF"
        set_leds(leds, 0, 0, 0)
        set_lcd_line(lcd_state, 1, "Ready")
        set_lcd_line(lcd_state, 2, "")
        return "OK OFF"

    if command.startswith("TEXT "):
        message = command[5:]
        set_lcd_line(lcd_state, 2, message[:16])
        return "OK TEXT"

    return "ERR INVALID_COMMAND"


def update_button(button, state, now):
    reading = button.value()
    if reading != state["candidate"]:
        state["candidate"] = reading
        state["changed_at"] = now

    if (
        reading != state["stable"]
        and time.ticks_diff(now, state["changed_at"]) >= DEBOUNCE_MS
    ):
        state["stable"] = reading
        if reading == 1:
            state["armed"] = True
        elif state["armed"]:
            state["armed"] = False
            send_reply("EVT BUTTON")


def main():
    leds = {
        "green": Pin(GREEN_PIN, Pin.OUT),
        "yellow": Pin(YELLOW_PIN, Pin.OUT),
        "red": Pin(RED_PIN, Pin.OUT),
    }
    set_leds(leds, 0, 0, 0)

    lcd_state = [None]
    try:
        lcd_state[0] = create_lcd()
    except Exception as error:
        debug("LCD unavailable: " + repr(error))
    set_lcd_line(lcd_state, 1, "Ready")
    set_lcd_line(lcd_state, 2, "")

    button = Pin(BUTTON_PIN, Pin.IN, Pin.PULL_UP)
    now = time.ticks_ms()
    initial_reading = button.value()
    button_state = {
        "candidate": initial_reading,
        "stable": initial_reading,
        "changed_at": now,
        "armed": initial_reading == 1,
    }

    state = {
        "mode": "OFF",
        "blink_on": False,
        "next_blink": now,
    }
    poller = uselect.poll()
    poller.register(sys.stdin, uselect.POLLIN)
    line_buffer = []
    discarding_oversized_line = False

    try:
        while True:
            now = time.ticks_ms()
            update_button(button, button_state, now)

            if (
                state["mode"] == "UNKNOWN"
                and time.ticks_diff(now, state["next_blink"]) >= 0
            ):
                state["blink_on"] = not state["blink_on"]
                led_value = 1 if state["blink_on"] else 0
                set_leds(leds, led_value, led_value, led_value)
                state["next_blink"] = time.ticks_add(now, BLINK_INTERVAL_MS)

            # Keep each pass bounded so queued serial traffic cannot starve the
            # button debounce check or the blink timer.
            chars_read = 0
            while (
                chars_read < MAX_INPUT_CHARS_PER_LOOP
                and poller.poll(0)
            ):
                char = sys.stdin.read(1)
                if not char:
                    break
                chars_read += 1

                if char == "\n":
                    if discarding_oversized_line:
                        send_reply("ERR INVALID_COMMAND")
                    else:
                        command = "".join(line_buffer)
                        if command.endswith("\r"):
                            command = command[:-1]
                        reply = handle_command(command, leds, lcd_state, state, now)
                        send_reply(reply)
                    line_buffer = []
                    discarding_oversized_line = False
                elif not discarding_oversized_line:
                    if len(line_buffer) >= MAX_LINE_LENGTH:
                        line_buffer = []
                        discarding_oversized_line = True
                    else:
                        line_buffer.append(char)
    finally:
        set_leds(leds, 0, 0, 0)


if __name__ == "__main__":
    main()