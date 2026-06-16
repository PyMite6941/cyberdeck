# deck-gpio — GPIO/I2C/SPI rapid prototyper

Turn the cyberdeck into a live hardware-hacking station. Describe a device:

```
deck-gpio --map i2c 0x3c ssd1306
deck-gpio --map gpio 17 led --execute
deck-gpio --map spi cs0 mcp3008 --execute
deck-gpio --list-devices
```

It prints (or runs) a ready-to-use Python script — boilerplate (imports,
bus init, device setup) already written, just watch the output.

## How it works

1. You pass `--map BUS ADDR DRIVER` — e.g. `--map i2c 0x76 bme280`.
2. The script looks up the driver in its built-in template table, fills in
   the address, and generates a complete Python test program.
3. With `--execute` (`-x`), it runs that program and shows the result.
4. With `--with-claude`, it also asks Claude Code to generate an enhanced
   version (falls back to the built-in template if Claude isn't available).

## Known devices

Run `deck-gpio --list-devices` to see all templates:

| Bus  | Device   | Default Address | Template                                   |
|------|----------|----------------|--------------------------------------------|
| I2C  | ssd1306  | 0x3c           | 128×64 OLED display test                   |
| I2C  | bme280   | 0x76           | Temperature/humidity/pressure sensor        |
| I2C  | ads1115  | 0x48           | 16-bit 4-channel ADC                       |
| I2C  | mpu6050  | 0x68           | 6-axis IMU (accel + gyro)                  |
| I2C  | pca9685  | 0x40           | 16-channel PWM/servo controller            |
| I2C  | pn532    | 0x24           | NFC/RFID reader                            |
| SPI  | mcp3008  | cs0            | 8-channel 10-bit ADC                       |
| SPI  | rfm9x    | cs0            | LoRa radio module (923 MHz AS923)          |
| GPIO | led      | 17             | Blink an LED                               |
| GPIO | button   | 2              | Read a push button with pull-up            |
| GPIO | hc-sr04  | 23,24          | Ultrasonic distance sensor (trig, echo)    |
| UART | gps      | /dev/serial0   | NMEA GPS receiver                          |

## Extending

Add new devices by editing `deck-gpio.py` — append to the `TEMPLATES` dict.
Each entry needs a `Device(bus, addr, driver, template_str)` with `{addr}`
as the placeholder for the address the user passes.

## Requirements

- Template generation works with just Python (any platform).
- **Execution on the Pi** needs the hardware library (RPi.GPIO, Blinka,
  the adafruit-* for your device). Install via the shared venv:
  `../setup-venv.sh` then `pip install adafruit-circuitpython-ssd1306`
  (or whatever your device needs).
- **`--with-claude`** needs `claude` on PATH (Claude Code CLI).
