# deck-radio

RTL-SDR front-end for the deck. Wraps the standard `rtl-sdr` toolchain
(`rtl_test`, `rtl_power`, `rtl_fm`, `rtl_433`, `dump1090`, `rtl_ais`) behind a
themed TUI: detect dongles, sweep a band, or launch a decoder (FM, ADS-B, AIS,
433 MHz ISM). The UI opens even with nothing installed and tells you what's
missing.

CLI + Textual TUI, cyberdeck theme.

```bash
./run.sh                 # TUI
./run.sh --devices       # list detected RTL-SDR devices
./run.sh --scan 88M:108M # CLI band sweep
```

System deps (apt, not pip):

```bash
sudo apt install rtl-sdr rtl-433 dump1090-fa
```
