---
layout: page
title: "Hardware Setup — Firmware Patching Journey"
permalink: /hardware-setup/
---

# Hardware Setup — Firmware Patching Journey

> Getting `nexmon_csi` running reliably meant working through four different hardware/network arrangements before landing on a stable one. Each iteration failed for a different reason — usually related to how monitor mode interacts with the Pi's network interface, or how the host machine handles power to a connected Pi.

This page walks through that progression, then covers the OS/kernel/firmware dependency issues that had to be resolved alongside it.

---

## Why this took multiple attempts

Activating monitor mode via `nexmon_csi` patches the Wi-Fi chip's firmware directly. The moment that happens, standard communication over `wlan0` drops — so whatever you were using to talk to the Pi (SSH over Wi-Fi, in particular) goes down with it. Every setup below is really just a different answer to the question: **once `wlan0` is gone, how do you still talk to the Pi, and how does the Pi still get network access for capture?**

---

## Setup 1: Mobile Hotspot Interface (Wireless SSH)

All hosts communicated wirelessly over a mobile hotspot, with Trixie OS flashed to the SD card. `nexmon_csi` was installed and compiled as-is.

**Failure point:** as expected, patching the firmware to enable monitor mode killed the `wlan0` link — and with it, the SSH session. A physical connection turned out to be non-negotiable once the firmware is patched.

## Setup 2: Ethernet Interface

To get around the `wlan0` problem, the Pi was connected directly to a laptop via a USB-to-Ethernet adapter, giving it a network path outside of Wi-Fi entirely.

**Failure point:** the connection was flaky rather than broken. Laptop USB ports manage power output tightly, and the Ethernet link would drop during anything resource-intensive — cloning large repositories, for example.

> `tmux` sessions can keep work alive through these drops, but that's a workaround, not a fix. A more stable hardware configuration was still needed.

## Setup 3: Router Interface (Standalone)

This setup removed the laptop from the Pi's network path altogether. The Pi runs independently with its own monitor and keyboard, monitoring the router directly, while the laptop's only job is to continuously send UDP packets across the network for the Pi to capture.

**Result:** this solved the connectivity drops, because the capture device was no longer dependent on the laptop's power-management behavior at all.

## Setup 4: Final Distributed Setup

The working configuration splits the two roles across two separate Raspberry Pis:

- **Raspberry Pi 3 (transmitter):** dedicated to continuously pinging UDP packets through the network.
- **Raspberry Pi 4 (receiver/capturer):** dedicated solely to capturing the resulting CSI data.

Neither device depends on a laptop's network stack, which is what made this the setup that finally stuck.

---

## Software & dependency troubleshooting

Even with the hardware settled, the bigger and more persistent hurdle was aligning OS, kernel, and firmware versions to what `nexmon_csi` actually supports.

**Hardware constraints, per the Nexmon docs:**

- **Raspberry Pi 4** — chip `bcm43455c0`, with 4 available firmware patches, each tied to a specific kernel.
- **Raspberry Pi 3** — chip `bcm43430a1`, with 2 available firmware patches, each tied to a specific kernel.

### The update loop issue

Flashing an older, compatible Bullseye image and installing the matching firmware version solves the problem — until you run a routine `apt update` to pull in other required libraries. That update quietly pulls in a newer kernel and firmware, silently breaking the `nexmon_csi` patch.

The fix is to hold the Pi-specific packages so the rest of the system can still update normally:

```bash
sudo apt-mark hold raspberrypi-kernel raspberrypi-kernel-headers raspberrypi-bootloader
```

### Legacy repository challenges

Some of the older images needed are old enough that their standard package mirrors have since been deprecated for security reasons. The fix is to manually point `/etc/apt/sources.list` and `/etc/apt/sources.list.d/raspi.list` at an archive/legacy mirror so library installs can still go through:

```bash
sudo nano /etc/apt/sources.list
sudo nano /etc/apt/sources.list.d/raspi.list
# Update the entries to the appropriate archive/legacy mirror for your OS release, then:
sudo apt update
```

### Kernel & firmware mismatches

Two other approaches were tried and ruled out before landing on the final configuration:

| Attempt | Approach | Why it failed |
|---|---|---|
| 1 | Ran an older kernel built for the Pi 3 on a Pi 4 | The Pi 4's newer architecture requirements weren't met. |
| 2 | Downgraded Pi 3 firmware to meet Nexmon's requirements | The older firmware no longer met current network security standards, causing total loss of network access. |

---

## Reference: default OS image versions

Kernel and firmware versions shipped by default in the older Raspberry Pi OS images used during testing, before any modification:

| OS Image | Firmware Version | Kernel Version |
|---|---|---|
| `2021-10-30-raspios-bullseye-armhf-lite` | 7.45.229 | 5.10.63-v7+ |
| `2022-01-28-raspios-bullseye-armhf-lite` | 7.25.241 | 5.10.92-v7+ |
| `2021-05-07-raspios-buster-armhf-lite` | 7.45.229 | 5.10.17-v7+ |
| `2021-01-11-raspios-buster-armhf-lite` | 7.45.98.94 | 5.4.83-v7 |
| `2021-03-04-raspios-buster-armhf-lite` | 7.45.98.94 | 5.10.17-v7+ |

## Reference: Nexmon firmware patch specifications

Straight from the `nexmon_csi` repository — the strict hardware/firmware/kernel combinations it supports.

**Raspberry Pi 3 (chip `bcm43430a1`)**

| Firmware Patch Version | Supported Hardware | OS / Target Kernel |
|---|---|---|
| `7_45_41_26` | Raspberry Pi 3 and Zero W | Raspbian 8 |
| `7_45_41_46` | Raspberry Pi 3 and Zero W | Raspbian Stretch |

**Raspberry Pi 4 (chip `bcm43455c0`)**

| Firmware Patch Version | Supported Hardware | OS / Target Kernel |
|---|---|---|
| `7_45_154` | Raspberry Pi B3+/B4 | Raspbian Kernel 4.9/14/19 |
| `7_45_189` | Raspberry Pi B3+/B4 | Raspbian Kernel 4.14/19, 5.4 |
| `7_45_206` | Raspberry Pi B3+/B4 | Raspberry Pi OS Kernel 5.4 |
| `7_45_234 (4ca95bbcy)` | Raspberry Pi B3+/B4/5 | Raspberry Pi OS |

---

## Final working configuration

After all of the above, this is what stabilized on the **Raspberry Pi 4**:

- **Kernel:** 5.10 *(5.4 was tested but refused to boot the OS)*
- **Firmware:** downgraded to `7.45.189` — compatible with both modern network access and the Nexmon patch
- **Result:** `nexmon_csi` installed and ran correctly, enabling Setup 4 above

---

## Takeaways for next time

- Don't rely on wireless SSH once you're about to patch firmware — plan for Ethernet or a fully standalone Pi from the start.
- Laptop USB/Ethernet ports aren't reliable for sustained, resource-heavy sessions with a Pi; power management will get in the way eventually.
- The cleanest setup decouples roles entirely: one device transmits, one captures, neither depends on a laptop.
- Hold `raspberrypi-kernel`, `raspberrypi-kernel-headers`, and `raspberrypi-bootloader` *before* running `apt update` on any patched system.
- Cross-check the Nexmon compatibility tables against your Pi's Wi-Fi chip before flashing an image — it saves a lot of rework.
