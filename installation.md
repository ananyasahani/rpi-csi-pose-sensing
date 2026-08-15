---
title: Installation
---

# Installation

[Home](index.md) | [FAQ](faq.md)

## Requirements

- Raspberry Pi 4 Model B
- Raspberry Pi OS Lite 64-bit (flashed via `rpi-imager`)
- SSH access to the Pi (key-based auth recommended)
- A second machine to build the firmware patch from

## Steps

### 1. Flash the OS

Flash Raspberry Pi OS Lite 64-bit to an SD card and enable SSH before first
boot (either via `rpi-imager`'s advanced options or by dropping an empty
`ssh` file in the boot partition).

### 2. Set up SSH access

Set up RSA key-based SSH access to the Pi. If you need to write
`authorized_keys` directly onto the SD card's rootfs (e.g. the Pi isn't
reachable over the network yet), you can mount the card via a USB reader.

### 3. Clone nexmon_csi and build

```bash
git clone https://github.com/seemoo-lab/nexmon_csi
cd nexmon_csi
source setup_env.sh   # or however your NEXMON_SETUP_ENV is set
```

Use the `Makefile.rpi` build method — this avoids needing a modified
`brcmfmac` driver, which the older approach required.

> **Note:** if you hit `"recipe commences before first target"`, check that
> `Makefile.rpi` wasn't corrupted or truncated during clone — re-clone if so.

Build inside a `tmux` session if you're over SSH, since monitor mode can
drop WiFi connectivity mid-build.

### 4. Load the patch and bring up monitor mode

Follow the `Makefile.rpi` instructions to load the patched firmware and
bring up the `mon0` monitor-mode interface.

### 5. Configure CSI capture parameters

Use `nexutil` (bundled with nexmon_csi) to set the CSI parameter string —
this defines which channel, bandwidth, and MAC filtering to use for capture.

### 6. Capture CSI frames

Start a packet capture (e.g. with `tcpdump` on `mon0`) to record CSI frames
from ambient traffic. Frames are embedded in the radiotap header of
captured packets and can be parsed out with the nexmon_csi Python tools.

## Fallback: serial console access

If monitor mode knocks the Pi off WiFi and you lose SSH, a UART console
(e.g. via an ESP32's CP2102 USB-serial chip wired to the Pi's GPIO UART
pins) gives you a way back in without needing a monitor and keyboard.

## Troubleshooting

- **`apt-get update` fails with 404 on Buster-based images**: the
  `raspbian.raspberrypi.org` and `archive.raspberrypi.org` Buster suites
  have shifted; consider moving to a currently-supported OS image instead
  of chasing archived repos.
- **Build environment not persisting**: re-source `setup_env.sh` in each
  new shell/tmux pane, and use `sudo -E` if commands need root but still
  need `NEXMON_SETUP_ENV` in scope.
