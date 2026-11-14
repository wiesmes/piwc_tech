# Pico wiring

This document records the P1 wiring for the original RP2040 Raspberry Pi Pico.
All components share Pico GND. Do not connect any LEDs, button, or optional
display until the Pico pin numbering has been checked against the board.

| Component | GPIO | Physical pin | Notes |
|---|---:|---:|---|
| Green LED | GP14 | 19 | Own 220-ohm series resistor; cathode to GND |
| Yellow LED | GP15 | 20 | Own 220-ohm series resistor; cathode to GND |
| Red LED | GP16 | 21 | Own 220-ohm series resistor; cathode to GND |
| Button | GP17 | 22 | Switch between GP17 and GND; internal pull-up enabled |
| Optional I2C0 SDA | GP0 | 1 | LCD only, disabled in firmware by default |
| Optional I2C0 SCL | GP1 | 2 | LCD only, disabled in firmware by default |
| Common ground | GND | e.g. 18 or 23 | Common to Pico, LEDs, button, and LCD if used |

For each LED, connect its GPIO through a separate 220-ohm resistor to the
anode; connect the cathode to ground. The firmware turns an LED on by driving
its GPIO high. The button's other terminal goes to GND, not 3.3 V. The internal
pull-up makes the input high while released and low while pressed.

LCD wiring is optional. Do not guess its controller, supply voltage, I2C
address, or backpack pin mapping. Identify the module and check its datasheet
before powering it. Verify that SDA/SCL pull-ups rise to no more than the Pico's
3.3 V GPIO level; a 5 V pull-up requires a suitable level shifter or a verified
3.3 V pull-up arrangement. Never connect 5 V pull-ups directly to GP0/GP1.
Connect LCD ground to the same common ground.

LCD support remains disabled (`LCD_ENABLED = False`) until these checks are
complete. The optional driver in `pico/lcd_i2c.py` supports only an identified
PCF8574 backpack with an HD44780-compatible 16x2 display; its common default
pin mapping must also be verified for the actual module. See
[`pico/README.md`](../pico/README.md) for LCD identification and test steps.