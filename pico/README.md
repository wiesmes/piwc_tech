# Pico hardware controller

The Raspberry Pi 5 (or a Windows development laptop) sends newline-terminated
commands over USB to the original RP2040 Raspberry Pi Pico. The Pico handles the
button, three bin LEDs, and—when deliberately enabled—a 16x2 I2C LCD. The
firmware accepts the same serial protocol regardless of which host is connected.

## Wiring

| Part | Pico GPIO | Physical Pico pin | Connection |
|---|---:|---:|---|
| Green LED | GP14 | 19 | GP14 through its own 220-ohm resistor to LED anode; cathode to GND |
| Yellow LED | GP15 | 20 | GP15 through its own 220-ohm resistor to LED anode; cathode to GND |
| Red LED | GP16 | 21 | GP16 through its own 220-ohm resistor to LED anode; cathode to GND |
| Button | GP17 | 22 | One side to GP17, the other side to GND; firmware enables the internal pull-up |
| Optional LCD SDA | GP0 | 1 | I2C0 SDA |
| Optional LCD SCL | GP1 | 2 | I2C0 SCL |
| Common ground | — | e.g. 18 or 23 | Join Pico, LEDs, button, and any LCD ground |

With the LED wiring shown, a GPIO output of 1 turns that LED on. Keep each
220-ohm resistor in series with its own LED; the resistor may be on either side
of the LED. The button reads high when released and low when pressed. Do not
connect the button to a GPIO and 3.3 V at the same time. All components must
share ground.

### Identify and check an LCD before connecting it

LCD support is **disabled by default** (`LCD_ENABLED = False` in `main.py`).
The firmware and LED/button features work without an LCD.

Do not guess the LCD controller, supply voltage, I2C address, or backpack
pin mapping. Read the module/backpack labels and datasheet, or ask the hardware
owner to identify them. Confirm the permitted supply voltage before powering
the module. Check the backpack's SDA/SCL pull-ups: Pico GPIO is 3.3 V and is
not 5 V tolerant. Pull-ups must go to 3.3 V (or use a suitable I2C level
shifter); never connect 5 V pull-ups directly to GP0/GP1. Share ground.

The optional `lcd_i2c.py` driver is for a **verified PCF8574 backpack with an
HD44780-compatible 16x2 LCD**. Its default expander pin mapping is common, not
universal. Confirm the chip and mapping, then adjust the driver's mapping
arguments if the module differs. To discover the address after wiring a
confirmed-safe module, run this in the Thonny REPL:

```python
from machine import I2C, Pin
i2c = I2C(0, sda=Pin(0), scl=Pin(1), freq=100000)
print([hex(address) for address in i2c.scan()])
```

Only use an address returned by the scan and confirmed against the module. No
LCD address is assumed in the firmware.

## Install MicroPython with Thonny

1. Connect the Pico to the computer with a USB data cable.
2. In Thonny, open **Tools → Options → Interpreter** and choose **MicroPython
   (Raspberry Pi Pico)**.
3. If prompted to install or update MicroPython, select the original Raspberry
   Pi Pico / RP2040 target and follow Thonny's prompts. Do not select Pico W.
4. Wait for Thonny to reconnect and show the MicroPython prompt.

## Copy the files to the Pico

In Thonny, open `pico/main.py` and `pico/lcd_i2c.py` from this project. For each,
choose **File → Save as… → Raspberry Pi Pico** and save it on the board with
the exact filename `main.py` or `lcd_i2c.py`. The LCD driver is not imported
unless LCD support is enabled, but copy it now so it is available after the
module is identified. Press **Stop/Restart** in Thonny to run the current
program; saving `main.py` to the board also makes it run on the next power-up.

## First test: only the three LEDs

1. Leave the LCD disconnected. Wire only the three LEDs, each with its own
   220-ohm series resistor, and connect their cathodes to Pico GND.
2. Check the pin table and inspect for shorts before connecting USB.
3. Connect the Pico and run `main.py` from Thonny. All LEDs should start off.
4. In Thonny's MicroPython Shell, enter `RECYCLE` and press Enter. The green
   LED should turn on and the shell should show `OK RECYCLE`.
5. Try `COMPOST`, `LANDFILL`, and `OFF`; each reply and expected single LED
   state is listed below. Confirm each new command turns the previous LED off.

## Serial commands and replies

Send each command followed by a newline (Enter). Replies are newline-terminated
ASCII:

| Command | Expected reply | LED behavior |
|---|---|---|
| `RECYCLE` | `OK RECYCLE` | Green on; yellow and red off |
| `COMPOST` | `OK COMPOST` | Yellow on; green and red off |
| `LANDFILL` | `OK LANDFILL` | Red on; green and yellow off |
| `UNKNOWN` | `OK UNKNOWN` | All three blink together, changing every 500 ms |
| `OFF` | `OK OFF` | All off |
| `TEXT Hello` | `OK TEXT` | No LED change; on an enabled LCD, line 2 shows `Hello` |

`UNKNOWN` shows `CHECK PACKAGING` on LCD line 1 when an LCD is enabled. `TEXT`
changes only line 2, truncates at 16 characters, and pads the rest of the line
to erase old text. An invalid command replies `ERR INVALID_COMMAND` and does
not change the current state.

## Button and blinking tests

With the button wired from GP17 to GND, run the firmware and press/release it.
The host should receive exactly one `EVT BUTTON` per debounced press. Holding
the button must not repeat the event. If the button is held while the Pico
starts, release it before testing a new press.

Send `UNKNOWN`: all LEDs should blink together on/off at 500 ms intervals.
While they blink, send `OFF` or a bin command; the new command should take
effect immediately and blinking should stop.

## Enable and test the LCD

Only after identifying the LCD supply, controller, I2C address, pull-up voltage,
and expander mapping:

1. Wire I2C0 SDA/SCL to GP0/GP1 and connect a common ground. Verify SDA/SCL
   cannot rise above Pico-safe 3.3 V levels.
2. Run the address scan above and record the confirmed address.
3. In `main.py`, set `LCD_ENABLED = True` and set `LCD_I2C_ADDRESS` to that
   verified numeric address (for example, the address reported by the scan).
   If necessary, change the PCF8574 mapping arguments in `create_lcd()` to
   match the identified backpack.
4. Save the updated `main.py` to the Pico, restart, and check for `Ready` on
   line 1 with line 2 blank. Test the bin commands, `UNKNOWN`, `OFF`, and
   `TEXT A longer message here` and confirm line 2 truncates/pads correctly.
5. If the screen stays blank or wiring/module details remain uncertain, turn
   `LCD_ENABLED` back off and continue using the firmware without the LCD.

LCD initialization and write failures are contained: the firmware disables LCD
updates and continues controlling the LEDs, serial commands, and button.

## Test from a Windows laptop

The Pico's USB serial connection can be tested before connecting it to the Pi
5. First run/save the firmware on the Pico, then close Thonny so it releases
the COM port. In PowerShell, replace `COM5` with the Pico's COM port from
**Device Manager → Ports (COM & LPT)**:

```powershell
$port = New-Object System.IO.Ports.SerialPort 'COM5',115200,'None',8,'One'
$port.NewLine = "`n"
$port.ReadTimeout = 2000
$port.Open()
$port.WriteLine('RECYCLE')
$port.ReadLine()
$port.Close()
```

The command should print `OK RECYCLE`. Change the text passed to `WriteLine`
to test the other commands. Set `NewLine` to LF; the firmware also accepts
CRLF. USB CDC does not generally use the baud rate as a physical timing
setting, but `115200` is a conventional host configuration and matches a
typical backend serial setup. On Linux, the Pico commonly appears as
`/dev/ttyACM0`; use the actual device name reported by the system.

Close Thonny before the backend or another serial client opens the port; only
one program can own it at a time. After changing firmware or releasing the
port, unplug and replug the Pico to restart it.

## Software checks and hardware checks

The source can be checked for Python syntax without connecting hardware. LED
polarity, the actual pin wiring, button debounce, USB serial behavior, LCD
voltage safety, controller compatibility, I2C address, and display output
require tests on the identified physical components.
