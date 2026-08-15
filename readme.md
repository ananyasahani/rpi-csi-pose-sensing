# RPi CSI Pose Sensing

WiFi Channel State Information (CSI) capture and human pose sensing on
Raspberry Pi 4, using [nexmon_csi](https://github.com/seemoo-lab/nexmon_csi)
for firmware-level CSI extraction from ambient WiFi traffic — explored as an
alternative to camera-based pose detection.

📄 **Full documentation:** [ananyasahani.github.io/rpi-csi-pose-sensing](https://ananyasahani.github.io/rpi-csi-pose-sensing/)

## Overview

- **Hardware**: Raspberry Pi 4 Model B (bcm43455c0 chipset)
- **Firmware patch**: nexmon_csi, built via the `Makefile.rpi` method
- **OS**: Raspberry Pi OS Lite 64-bit
- **Capture mode**: monitor-mode WiFi interface (`mon0`), extracting CSI
  from ambient nearby traffic (no dedicated sender/receiver pair)
- **Alternative path explored**: ESP32-native CSI capture via Espressif's
  [esp-csi](https://github.com/espressif/esp-csi)

See the [Installation guide](https://ananyasahani.github.io/rpi-csi-pose-sensing/installation.html)
for full setup steps.

## Status

Actively in progress — monitor-mode and firmware patching confirmed working;
CSI capture and storage pipeline is the current focus.
