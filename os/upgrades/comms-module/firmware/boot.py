# DFCD comms-module — runs once at Pico power-on, before code.py.
# Enables the second USB serial (data CDC) that the deck's deck-comms talks to,
# while keeping the normal console CDC for debugging.
import usb_cdc

usb_cdc.enable(console=True, data=True)
