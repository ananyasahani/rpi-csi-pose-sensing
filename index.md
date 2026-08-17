---
title: WiFi CSI Human Pose Sensing
---

# WiFi CSI Human Pose Sensing

[Overview](#overview) | [Installation](installation.md) | [Capture Pipeline](#capture-pipeline) | [Fundametals](csi_preprocessing.md) [GitHub](https://github.com/ananyasahani/rpi-csi-pose-sensing)

## Overview

This project captures WiFi Channel State Information (CSI) on a Raspberry Pi 4B
using [nexmon_csi](https://github.com/seemoo-lab/nexmon_csi), a firmware patch
that exposes fine-grained CSI data from the Broadcom WiFi chipset. The goal is
to explore CSI-based human pose sensing — detecting body position and movement
from ambient WiFi traffic — as a privacy-preserving, non-visual alternative to
camera-based pose detection.

Unlike setups that require a dedicated sender/receiver pair, this project
targets **ambient capture**: extracting CSI from WiFi traffic that is already
present in the environment, rather than generating a controlled traffic stream.

## Motivation

Camera-based human pose estimation is effective but has clear downsides:
it requires line of sight, is sensitive to lighting, and raises privacy
concerns. WiFi sensing offers an alternative — CSI reflects how the signal
is distorted by objects (including people) in its path, which can be used
to infer motion and pose without a camera in the room.

## Approach

- **Hardware**: Raspberry Pi 4 Model B (bcm43455c0 chipset)
- **Firmware patch**: nexmon_csi, built via the `Makefile.rpi` method
  (no modified `brcmfmac` driver required)
- **OS**: Raspberry Pi OS Lite 64-bit
- **Capture mode**: monitor-mode WiFi interface (`mon0`) extracting CSI
  from ambient nearby traffic
- **Alternative path explored**: ESP32-native CSI capture via Espressif's
  [esp-csi](https://github.com/espressif/esp-csi) project, evaluated
  alongside the Raspberry Pi route

## Capture Pipeline

1. Flash Raspberry Pi OS Lite 64-bit
2. Build and load the nexmon_csi firmware patch (`Makefile.rpi`)
3. Bring up the monitor-mode interface and configure the CSI parameter string
4. Capture raw CSI frames from ambient WiFi traffic
5. Post-process captured frames for downstream pose-sensing analysis

See [Installation](installation.md) for the full step-by-step setup.

## Status

Actively in progress — monitor-mode and firmware patching confirmed working;
CSI capture and storage pipeline is the current focus.

## Team

This project is being built by:

- **Ananya Sahani**
- **Sandeep Balaji**
- **Hemesh Kukreja**

## Publications

_None yet — this section will be updated if the project results in a paper
or writeup
