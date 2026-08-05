# deck-sensors

Live monitor for the deck's SoC and any attached HAT/I2C environment sensors.
Reads CPU temperature, memory, and uptime via `deck-lib/pi_sensors`, plus an
optional BME280-style I2C sensor (temp/humidity/pressure) if one is wired up.
Logs readings to SQLite. Off-Pi or with no sensor, missing values read `n/a`.

CLI + Textual TUI, cyberdeck theme.

```bash
./run.sh                 # live TUI
./run.sh --once          # print one reading, exit
./run.sh --log env.db    # tee readings to a SQLite file while running
```

Optional hardware sensor support: uncomment the Adafruit lines in
`requirements.txt` (Pi only).
