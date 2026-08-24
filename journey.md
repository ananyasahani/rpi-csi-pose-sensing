---
layout: page
title: "CSI Capture: Firmware Patching & Hardware Setup Journey"
permalink: /hardware-setup/
---

# CSI Capture: Firmware Patching & Hardware Setup Journey

## Overview

This document outlines the iterative process of establishing a Channel State Information (CSI) capture environment using the `nexmon_csi` repository. It details the progression through four distinct hardware setups and the software dependency challenges resolved along the way to reach a stable configuration.

---

## Hardware & Network Iterations

### Setup 1: Mobile Hotspot Interface (Wireless SSH)

| | |
|---|---|
| **Configuration** | All hosts communicated wirelessly via SSH over a mobile hotspot network. |
| **OS** | Trixie OS flashed to the SD card. |
| **Process** | Installed `nexmon_csi` and compiled the setup. |

**Failure Point:** Activating monitor mode inherently modifies the Wi-Fi chip's firmware. This causes all standard communication over `wlan0` to drop, severing the SSH connection. A physical connection is required to communicate with the Raspberry Pi once the firmware is patched.

### Setup 2: Ethernet Interface

| | |
|---|---|
| **Configuration** | Raspberry Pi connected directly to a laptop via a USB-to-Ethernet adapter to gain network access outside of `wlan0`. |
| **Process** | Repeated the firmware patching process from Setup 1. |

**Failure Point:** The connection proved highly flaky. Laptop ports strictly manage power output, causing the Ethernet connection to drop during resource-intensive tasks (like cloning large repositories).

> **Note:** While `tmux` sessions can keep a session alive through these drops, a more stable hardware configuration was ultimately necessary.

### Setup 3: Router Interface (Standalone)

| | |
|---|---|
| **Configuration** | The Raspberry Pi operates as a fully independent system with its own dedicated monitor and keyboard, bypassing laptop-to-Pi communication entirely. |
| **Process** | The Raspberry Pi acts purely as the CSI data-capturing component (monitoring the router), while the laptop continuously pings UDP packets through the network. |
| **Result** | Solved the connectivity drops by isolating the capture device from the laptop's power-management limitations. |

### Setup 4: Final Distributed Setup

| Role | Device | Function |
|---|---|---|
| Transmitter | Raspberry Pi 3 | Dedicated to continuously pinging UDP packets through the network. |
| Receiver / Capturer | Raspberry Pi 4 | Dedicated solely to capturing the resulting CSI data. |

Two Raspberry Pis operating in tandem on the network — this is the configuration that stuck.

---

## Software & Dependency Troubleshooting

The most significant hurdle across all setups was aligning the operating system, kernel version, and Wi-Fi firmware to meet the strict dependencies of `nexmon_csi`.

### Hardware Constraints (per Nexmon Docs)

- **Raspberry Pi 4:** Chip `bcm43455c0` — requires a specific kernel/firmware combination (4 available patches).
- **Raspberry Pi 3:** Chip `bcm43430a1` — requires a specific kernel/firmware combination (2 available patches).

### The Update Loop Issue

When flashing compatible older Bullseye images and installing specific firmware versions, running a standard `apt update` to fetch required libraries would automatically upgrade the kernel and firmware — breaking the `nexmon_csi` patch.

**Solution:** Prevent these specific upgrades by holding the relevant packages, locking the system at compatible versions while still allowing other necessary libraries to update:

```bash
sudo apt-mark hold raspberrypi-kernel raspberrypi-kernel-headers raspberrypi-bootloader
```

### Legacy Repository Challenges

For significantly older images, standard mirrors no longer exist due to security deprecations.

**Solution:** Manually edit `/etc/apt/sources.list` and `/etc/apt/sources.list.d/raspi.list` to point to Debian archive/legacy repositories so library installations can proceed. (Replace the example mirror below with the actual legacy/archive mirror appropriate for your OS release.)

```bash
sudo nano /etc/apt/sources.list
sudo nano /etc/apt/sources.list.d/raspi.list
# Point entries to the relevant archive/legacy mirror before running apt update
```

### Kernel & Firmware Mismatches

| Attempt | Approach | Outcome |
|---|---|---|
| 1 | Ran an older kernel designed for the Pi 3 on the Pi 4 | **Failed** — the newer architecture requirements on the Pi 4 were not met. |
| 2 | Downgraded firmware on the Pi 3 to meet Nexmon requirements | **Failed** — the older firmware no longer met current network security standards, causing a total loss of network access. |

---

## Reference Tables

### Default OS Image Versions

Default kernel and firmware versions found in standard older Raspberry Pi OS images, prior to any modification:

| OS Image | Firmware Version | Kernel Version |
|---|---|---|
| `2021-10-30-raspios-bullseye-armhf-lite` | 7.45.229 | 5.10.63-v7+ |
| `2022-01-28-raspios-bullseye-armhf-lite` | 7.25.241 | 5.10.92-v7+ |
| `2021-05-07-raspios-buster-armhf-lite` | 7.45.229 | 5.10.17-v7+ |
| `2021-01-11-raspios-buster-armhf-lite` | 7.45.98.94 | 5.4.83-v7 |
| `2021-03-04-raspios-buster-armhf-lite` | 7.45.98.94 | 5.10.17-v7+ |

### Official Nexmon GitHub Specifications

Strict hardware, firmware, and kernel requirements dictated by the `nexmon_csi` repository.

**Raspberry Pi 3 (Chip: `bcm43430a1`)**

| Wi-Fi Chip | Firmware Patch Version | Supported Hardware | OS / Target Kernel |
|---|---|---|---|
| `bcm43430a1` | `7_45_41_26` | Raspberry Pi 3 and Zero W | Raspbian 8 |
| `bcm43430a1` | `7_45_41_46` | Raspberry Pi 3 and Zero W | Raspbian Stretch |

**Raspberry Pi 4 (Chip: `bcm43455c0`)**

| Wi-Fi Chip | Firmware Patch Version | Supported Hardware | OS / Target Kernel |
|---|---|---|---|
| `bcm43455c0` | `7_45_154` | Raspberry Pi B3+/B4 | Raspbian Kernel 4.9/14/19 |
| `bcm43455c0` | `7_45_189` | Raspberry Pi B3+/B4 | Raspbian Kernel 4.14/19, 5.4 |
| `bcm43455c0` | `7_45_206` | Raspberry Pi B3+/B4 | Raspberry Pi OS Kernel 5.4 |
| `bcm43455c0` | `7_45_234 (4ca95bbcy)` | Raspberry Pi B3+/B4/5 | Raspberry Pi OS |

---

## Final Working Configuration

After extensive testing, the following environment was successfully stabilized on the **Raspberry Pi 4**:

- **Kernel Version:** 5.10 *(Note: Kernel 5.4 was tested but refused to boot the OS.)*
- **Firmware Version:** Downgraded to `7.45.189` (compatible with modern network access and the Nexmon patch).
- **Result:** `nexmon_csi` installed and functioned correctly, enabling the successful deployment of Setup 4.

---

## Key Takeaways

- Activating monitor mode via `nexmon_csi` always breaks standard Wi-Fi (`wlan0`) connectivity — plan for an out-of-band connection (Ethernet, or a fully standalone Pi) rather than relying on wireless SSH.
- Laptop USB/Ethernet ports impose power-management limits that make them unreliable for sustained, resource-heavy sessions with a Pi.
- The cleanest architecture decouples roles entirely: one device transmits, one captures, and neither depends on a laptop's network stack.
- `apt update` is dangerous on a patched system — always hold `raspberrypi-kernel`, `raspberrypi-kernel-headers`, and `raspberrypi-bootloader` before updating anything else.
- Kernel and firmware versions are tightly coupled to the specific Wi-Fi chip (`bcm43430a1` for Pi 3, `bcm43455c0` for Pi 4) — cross-referencing the Nexmon compatibility tables before flashing an image saves significant rework.
