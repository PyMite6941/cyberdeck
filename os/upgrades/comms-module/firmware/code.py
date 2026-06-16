# DFCD comms-module bridge — CircuitPython for a Raspberry Pi Pico.
#
# Reads a PN532 (NFC, I2C) and an RFM9x/SX127x (LoRa, SPI), and exposes a simple
# line protocol over the USB data-CDC so the deck drives both over ONE USB cable
# (the module's only connection to the rail bus). The deck side is `deck-comms`.
#
# Protocol (newline-terminated, 115200 8N1 on the data CDC):
#   PING            -> PONG DFCD-COMMS
#   STATUS          -> NFC:<ok|absent> LORA:<ok|absent>
#   NFC             -> UID:04:A2:...   or  NONE   (one read, ~0.5s)
#   LORA TX <text>  -> OK
#   LORA RX <secs>  -> LISTENING <secs>, then RX:<rssi>:<text> per packet, END
#
# Setup: flash CircuitPython to the Pico, then copy this file, boot.py, and the
# adafruit_pn532 + adafruit_rfm9x + adafruit_bus_device libs to CIRCUITPY.
# Wiring (Pico GPIO):
#   PN532  : SDA=GP4, SCL=GP5, 3V3, GND        (I2C0)
#   RFM9x  : SCK=GP18, MOSI=GP19, MISO=GP16, CS=GP17, RST=GP20, 3V3, GND  (SPI0)
import time
import board
import busio
import digitalio
import usb_cdc

LORA_FREQ = 923.0   # AS923 / Thailand — match the module you bought

serial = usb_cdc.data

i2c = busio.I2C(board.GP5, board.GP4)
spi = busio.SPI(board.GP18, MOSI=board.GP19, MISO=board.GP16)

pn532 = None
try:
    from adafruit_pn532.i2c import PN532_I2C
    pn532 = PN532_I2C(i2c, debug=False)
    pn532.SAM_configuration()
except Exception:
    pn532 = None

rfm = None
try:
    import adafruit_rfm9x
    _cs = digitalio.DigitalInOut(board.GP17)
    _rst = digitalio.DigitalInOut(board.GP20)
    rfm = adafruit_rfm9x.RFM9x(spi, _cs, _rst, LORA_FREQ)
    rfm.tx_power = 20
except Exception:
    rfm = None


def writeln(s):
    if serial is not None:
        serial.write((s + "\n").encode())


def uid_str(uid):
    return ":".join("%02X" % b for b in uid)


buf = b""
listen_until = 0.0

while True:
    # while inside a LoRa receive window, stream packets as they arrive
    if rfm is not None and listen_until:
        if time.monotonic() < listen_until:
            pkt = rfm.receive(timeout=0.5)
            if pkt is not None:
                try:
                    txt = pkt.decode()
                except Exception:
                    txt = uid_str(pkt)
                writeln("RX:%d:%s" % (rfm.last_rssi, txt))
        else:
            listen_until = 0.0
            writeln("END")

    if serial is not None and serial.in_waiting:
        buf += serial.read(serial.in_waiting)
        if b"\n" in buf:
            line, _, buf = buf.partition(b"\n")
            cmd = line.decode().strip()
            if cmd == "PING":
                writeln("PONG DFCD-COMMS")
            elif cmd == "STATUS":
                writeln("NFC:%s LORA:%s"
                        % ("ok" if pn532 else "absent", "ok" if rfm else "absent"))
            elif cmd == "NFC":
                if pn532 is None:
                    writeln("ERR nfc-absent")
                else:
                    uid = pn532.read_passive_target(timeout=0.5)
                    writeln("UID:" + uid_str(uid) if uid else "NONE")
            elif cmd.startswith("LORA TX "):
                if rfm is None:
                    writeln("ERR lora-absent")
                else:
                    rfm.send(cmd[8:].encode())
                    writeln("OK")
            elif cmd.startswith("LORA RX"):
                if rfm is None:
                    writeln("ERR lora-absent")
                else:
                    parts = cmd.split()
                    secs = float(parts[2]) if len(parts) > 2 else 30.0
                    listen_until = time.monotonic() + secs
                    writeln("LISTENING %.0f" % secs)
            else:
                writeln("ERR unknown")
    time.sleep(0.01)
