"""Small driver for a verified PCF8574 backpack and HD44780-compatible LCD."""

import time


class PCF8574LCD:
    def __init__(
        self,
        i2c,
        address,
        columns=16,
        rs=0x01,
        rw=0x02,
        enable=0x04,
        backlight=0x08,
        data_pins=(0x10, 0x20, 0x40, 0x80),
    ):
        if not 0x08 <= address <= 0x77:
            raise ValueError("I2C address must be a verified 7-bit address")
        if len(data_pins) != 4:
            raise ValueError("Exactly four data pin masks are required")

        self.i2c = i2c
        self.address = address
        self.columns = columns
        self.rs = rs
        self.rw = rw
        self.enable = enable
        self.backlight = backlight
        self.data_pins = data_pins

        time.sleep_ms(50)
        self._write_nibble(0x03, False)
        time.sleep_ms(5)
        self._write_nibble(0x03, False)
        time.sleep_us(150)
        self._write_nibble(0x03, False)
        self._write_nibble(0x02, False)
        self._write_command(0x28)
        self._write_command(0x0C)
        self._write_command(0x06)
        self._write_command(0x01)
        time.sleep_ms(2)

    def _write_expander(self, value):
        self.i2c.writeto(self.address, bytes((value | self.backlight,)))

    def _write_nibble(self, value, is_data):
        output = self.rs if is_data else 0
        for bit_index in range(4):
            if value & (1 << bit_index):
                output |= self.data_pins[bit_index]

        output &= ~self.rw
        self._write_expander(output | self.enable)
        time.sleep_us(1)
        self._write_expander(output & ~self.enable)
        time.sleep_us(50)

    def _write_byte(self, value, is_data):
        self._write_nibble((value >> 4) & 0x0F, is_data)
        self._write_nibble(value & 0x0F, is_data)

    def _write_command(self, command):
        self._write_byte(command, False)
        if command in (0x01, 0x02):
            time.sleep_ms(2)

    def _write_character(self, character):
        self._write_byte(ord(character), True)

    def write_line(self, line, text):
        if line == 1:
            address = 0x00
        elif line == 2:
            address = 0x40
        else:
            raise ValueError("Line must be 1 or 2")

        self._write_command(0x80 | address)
        text = text[: self.columns].ljust(self.columns)
        for character in text:
            self._write_character(character)
