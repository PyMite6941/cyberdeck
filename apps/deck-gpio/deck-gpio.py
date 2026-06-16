#!/usr/bin/env python3
"""
deck-gpio — GPIO/I2C/SPI rapid prototyper for the cyberdeck.

Pass a pin description like:
    deck-gpio --map i2c 0x3c ssd1306
    deck-gpio --map gpio 17 led
    deck-gpio --map spi cs0 mcp3008

It auto-generates a test script for that layout, runs it (if --execute),
and prints results. Optionally pushes the prompt through Claude Code for
more complex wiring logic.

Device-family templates live in a lookup table; extend with --template-dir.
"""

from __future__ import annotations

import argparse
import re
import shlex
import subprocess
import sys
import textwrap
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


# ── device templates ──────────────────────────────────────────────────────────

@dataclass
class Device:
    bus: str        # i2c | spi | gpio | uart
    addr: str       # hex address for i2c, chip-select for spi, pin for gpio
    driver: str     # human name, eg "ssd1306" or "bme280"
    template: str   # Python code template


TEMPLATES: dict[str, Device] = {
    # ── I2C devices ──
    "ssd1306": Device("i2c", "0x3c", "ssd1306", textwrap.dedent("""\
        import board
        import busio
        import adafruit_ssd1306

        i2c = busio.I2C(board.SCL, board.SDA)
        while not i2c.try_lock():
            pass
        devices = i2c.scan()
        print(f"I2C devices found: {[hex(d) for d in devices]}")
        i2c.unlock()

        oled = adafruit_ssd1306.SSD1306_I2C(128, 64, i2c, addr={addr})
        oled.fill(0)
        oled.text("deck-gpio test", 0, 0, 1)
        oled.text("hello from deck!", 0, 16, 1)
        oled.show()
        print("SSD1306: display OK")
    """)),
    "bme280": Device("i2c", "0x76", "bme280", textwrap.dedent("""\
        import board
        import busio
        import adafruit_bme280

        i2c = busio.I2C(board.SCL, board.SDA)
        bme = adafruit_bme280.Adafruit_BME280_I2C(i2c, address={addr})
        print(f"Temperature: {bme.temperature:.1f} C")
        print(f"Humidity:    {bme.humidity:.1f} %")
        print(f"Pressure:    {bme.pressure:.1f} hPa")
    """)),
    "ads1115": Device("i2c", "0x48", "ads1115", textwrap.dedent("""\
        import board
        import busio
        import adafruit_ads1x15.ads1115 as ADS
        from adafruit_ads1x15.analog_in import AnalogIn

        i2c = busio.I2C(board.SCL, board.SDA)
        ads = ADS.ADS1115(i2c, address={addr})
        for ch in range(4):
            chan = AnalogIn(ads, ch)
            print(f"AIN{ch}: {chan.value:5d}  {chan.voltage:.3f} V")
    """)),
    "mpu6050": Device("i2c", "0x68", "mpu6050", textwrap.dedent("""\
        import board
        import busio
        import adafruit_mpu6050

        i2c = busio.I2C(board.SCL, board.SDA)
        mpu = adafruit_mpu6050.MPU6050(i2c, address={addr})
        print(f"Accel: {mpu.acceleration}")
        print(f"Gyro:  {mpu.gyro}")
        print(f"Temp:  {mpu.temperature:.1f} C")
    """)),
    "pca9685": Device("i2c", "0x40", "pca9685", textwrap.dedent("""\
        import board
        import busio
        from adafruit_servokit import ServoKit

        i2c = busio.I2C(board.SCL, board.SDA)
        kit = ServoKit(channels=16, i2c=i2c, address={addr})
        print("PCA9685: 16-channel PWM controller ready")
        for ch in range(4):
            kit.servo[ch].angle = 90
            print(f"  Servo {ch} → 90°")
            time.sleep(0.3)
    """)),
    "pn532": Device("i2c", "0x24", "pn532", textwrap.dedent("""\
        import board
        import busio
        from adafruit_pn532.i2c import PN532_I2C

        i2c = busio.I2C(board.SCL, board.SDA)
        pn532 = PN532_I2C(i2c, address={addr})
        pn532.SAM_configuration()
        print("PN532: waiting for NFC tag...")
        uid = pn532.read_passive_target(timeout=5)
        if uid:
            print(f"Tag UID: {uid.hex()}")
        else:
            print("No tag found (timeout)")
    """)),

    # ── SPI devices ──
    "mcp3008": Device("spi", "cs0", "mcp3008", textwrap.dedent("""\
        import board
        import busio
        import digitalio
        import adafruit_mcp3xxx.mcp3008 as MCP
        from adafruit_mcp3xxx.analog_in import AnalogIn

        spi = busio.SPI(board.SCK, board.MOSI, board.MISO)
        cs = digitalio.DigitalInOut(board.CE0)
        mcp = MCP.MCP3008(spi, cs)
        for ch in range(4):
            chan = AnalogIn(mcp, ch)
            print(f"CH{ch}: {chan.value:5d}  {chan.voltage:.3f} V")
    """)),
    "rfm9x": Device("spi", "cs0", "rfm9x", textwrap.dedent("""\
        import board
        import busio
        import digitalio
        import adafruit_rfm9x

        spi = busio.SPI(board.SCK, board.MOSI, board.MISO)
        cs = digitalio.DigitalInOut(board.D25)
        rst = digitalio.DigitalInOut(board.D17)
        rfm = adafruit_rfm9x.RFM9x(spi, cs, rst, 923.0)
        print(f"RFM9x: RSSI = {rfm.last_rssi} dBm")
        rfm.send(b"deck-gpio ping")
        print("RFM9x: packet sent")
    """)),

    # ── GPIO devices ──
    "led": Device("gpio", "17", "led", textwrap.dedent("""\
        import RPi.GPIO as GPIO
        import time

        GPIO.setmode(GPIO.BCM)
        GPIO.setup({addr}, GPIO.OUT)
        print("GPIO LED: blinking 5 times")
        for _ in range(5):
            GPIO.output({addr}, GPIO.HIGH)
            time.sleep(0.3)
            GPIO.output({addr}, GPIO.LOW)
            time.sleep(0.3)
        GPIO.cleanup({addr})
        print("GPIO LED: OK")
    """)),
    "button": Device("gpio", "2", "button", textwrap.dedent("""\
        import RPi.GPIO as GPIO
        import time

        GPIO.setmode(GPIO.BCM)
        GPIO.setup({addr}, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        print("GPIO button: press within 5 seconds...")
        start = time.monotonic()
        while time.monotonic() - start < 5:
            if not GPIO.input({addr}):
                print(f"Button pressed (pin {addr})")
                break
        else:
            print("No press detected (timeout)")
        GPIO.cleanup({addr})
    """)),
    "hc-sr04": Device("gpio", "23,24", "hc-sr04", textwrap.dedent("""\
        import RPi.GPIO as GPIO
        import time

        TRIG, ECHO = {addr}
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(TRIG, GPIO.OUT)
        GPIO.setup(ECHO, GPIO.IN)
        GPIO.output(TRIG, False)
        time.sleep(0.2)
        GPIO.output(TRIG, True)
        time.sleep(0.00001)
        GPIO.output(TRIG, False)
        while GPIO.input(ECHO) == 0:
            pulse_start = time.monotonic()
        while GPIO.input(ECHO) == 1:
            pulse_end = time.monotonic()
        dist = (pulse_end - pulse_start) * 17150
        print(f"HC-SR04: {dist:.1f} cm")
        GPIO.cleanup()
    """)),

    # ── UART devices ──
    "gps": Device("uart", "/dev/serial0", "gps", textwrap.dedent("""\
        import serial
        import pynmea2

        ser = serial.Serial({addr!r}, 9600, timeout=3)
        print("GPS: reading NMEA sentences...")
        for _ in range(5):
            line = ser.readline().decode("ascii", errors="replace")
            if line.startswith("$GPGGA"):
                msg = pynmea2.parse(line)
                print(f"  Fix: lat={msg.lat}, lon={msg.lon}, alt={msg.altitude}")
        ser.close()
    """)),
}


# ── CLI ───────────────────────────────────────────────────────────────────────

def build_script(device: Device, addr_override: str | None = None) -> str:
    addr = addr_override or device.addr

    # Allow hex (0x3c), chip-selects (cs0), GPIO pins (17, 23,24),
    # and UART paths (/dev/serial0, /dev/ttyUSB0). Block shell metacharacters.
    if not re.match(r'^[a-zA-Z0-9x,/_]+$', addr):
        raise ValueError(f"Unsafe address: {addr!r}")

    if device.bus == "gpio" and "," in addr:
        addr_py = addr  # keep as-is for multi-pin like "23,24"
    elif device.bus == "uart":
        addr_py = repr(addr)
    else:
        addr_py = addr

    header = textwrap.dedent(f"""\
        #! /usr/bin/env python3
        # Auto-generated by deck-gpio --map {device.bus} {device.addr} {device.driver}
        # {time.strftime('%Y-%m-%d %H:%M:%S')}
        import time

    """)

    body = device.template
    body = body.replace("{addr!r}", addr_py)
    body = body.replace("{addr}", addr_py)
    return header + body


def run_script(script: str, timeout: int = 10) -> tuple[int, str, str]:
    proc = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return proc.returncode, proc.stdout, proc.stderr


def list_devices() -> None:
    by_bus: dict[str, list[tuple[str, Device]]] = {}
    for name, dev in sorted(TEMPLATES.items()):
        by_bus.setdefault(dev.bus, []).append((name, dev))

    for bus, devices in sorted(by_bus.items()):
        print(f"\n{bus.upper()} devices:")
        for name, dev in devices:
            print(f"  {name:14s}  addr={dev.addr}")


def main() -> None:
    ap = argparse.ArgumentParser(
        description="GPIO/I2C/SPI rapid prototyper for the cyberdeck",
    )
    ap.add_argument("--map", nargs=3, metavar=("BUS", "ADDR", "DRIVER"),
                    help="Describe a device: e.g. 'i2c 0x3c ssd1306'")
    ap.add_argument("--execute", "-x", action="store_true",
                    help="Execute the generated script (default: print to stdout)")
    ap.add_argument("--timeout", type=int, default=10,
                    help="Script execution timeout in seconds (default: 10)")
    ap.add_argument("--list-devices", "-l", action="store_true",
                    help="List all known device templates and exit")
    ap.add_argument("--with-claude", action="store_true",
                    help="Also pipe the request through Claude Code for enhanced code gen")
    args = ap.parse_args()

    if args.list_devices:
        list_devices()
        return

    if not args.map:
        ap.print_help()
        print("\nExamples:")
        print("  deck-gpio --map i2c 0x3c ssd1306")
        print("  deck-gpio --map gpio 17 led --execute")
        print("  deck-gpio --map spi cs0 mcp3008 --execute")
        print("  deck-gpio --list-devices")
        sys.exit(1)

    bus, addr, driver = args.map

    device = TEMPLATES.get(driver.lower())
    if device is None:
        print(f"Unknown device '{driver}'. Use --list-devices to see known types.",
              file=sys.stderr)
        sys.exit(1)

    if device.bus != bus:
        print(f"Warning: '{driver}' normally uses bus '{device.bus}', "
              f"not '{bus}' — using your override.", file=sys.stderr)

    script = build_script(device, addr)

    if args.with_claude:
        prompt = (
            f"Generate a Python test script for a {device.bus.upper()} "
            f"device ({driver}) at address {addr} on a Raspberry Pi. "
            f"Use RPi.GPIO, busio, and adafruit_* libraries. "
            f"The script should probe the device, read basic data, and "
            f"print results. Include error handling."
        )
        try:
            result = subprocess.run(
                ["claude", "-p", prompt],
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode == 0:
                script = result.stdout
        except (FileNotFoundError, subprocess.TimeoutExpired):
            print("(Claude Code unavailable — using built-in template)", file=sys.stderr)

    if not args.execute:
        print(script)
        return

    print(f"Running test for {driver} ({device.bus.upper()} @ {addr})...")
    rc, out, err = run_script(script, args.timeout)

    if rc == 0:
        print("SUCCESS — output:")
    else:
        print(f"FAILED (exit code {rc}) — output:")
    print(out)
    if err:
        print("STDERR:", err, file=sys.stderr)

    sys.exit(rc)


if __name__ == "__main__":
    main()
