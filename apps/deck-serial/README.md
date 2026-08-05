# deck-serial

UART / serial console monitor for board bring-up in the field. Lists serial
ports, opens one at a chosen baud, streams incoming bytes to a themed log pane,
lets you type lines back, and can tee everything to a file. Pairs with
`deck-gpio`. Uses pyserial.

CLI + Textual TUI, cyberdeck theme.

```bash
./run.sh                                      # TUI (pick a port)
./run.sh --list                               # list serial ports
./run.sh --port /dev/ttyUSB0 --baud 115200    # open directly
./run.sh --port /dev/ttyUSB0 --log boot.txt   # + tee to a file
```
