# Nexmon CSI — Installation Guide

> Tested on **Raspberry Pi 4 Model B** and **Raspberry Pi 5** running  
> Raspberry Pi OS Lite 64-bit (Trixie, November 2025).  
> This guide combines the firmware downgrade step with the full Nexmon CSI build.

---

## What this does

Nexmon CSI lets your Raspberry Pi's Wi-Fi chip report **Channel State Information (CSI)** — raw signal measurements from every received Wi-Fi packet. This requires:

1. Replacing the default Wi-Fi firmware with an older patched version.
2. Building and installing the Nexmon CSI patch on top of that firmware.

---

## Prerequisites

- Raspberry Pi 4B or 5 with Raspberry Pi OS Lite 64-bit (Trixie)
- Internet access via Ethernet (Wi-Fi will go down during setup)
- SSH access or a keyboard/monitor connected

---

## Step 0 — Raspberry Pi 5 only: switch to the non-16K kernel

> **Skip this if you are on a Raspberry Pi 4.**

The default Pi 5 kernel uses 16K memory pages, which breaks the Nexmon build tools. Switch to the standard 4K-page kernel first:

```bash
sudo echo 'kernel=kernel8.img' >> /boot/firmware/config.txt
sudo reboot
```

Reconnect after reboot before continuing.

---

## Step 1 — Downgrade the Wi-Fi firmware

The Nexmon CSI patch targets firmware version `7.45.189`. Download it and replace the current firmware:

```bash
cd ~

# Download the patched firmware binary
curl -LO https://raw.githubusercontent.com/seemoo-lab/nexmon/master/firmwares/bcm43455c0/7_45_189/brcmfmac43455-sdio.bin

# Back up the current firmware (so you can restore it later)
sudo cp /lib/firmware/brcm/brcmfmac43455-sdio.bin ~/brcmfmac43455-sdio.bin.backup

# Install the older firmware
sudo cp brcmfmac43455-sdio.bin /lib/firmware/brcm/brcmfmac43455-sdio.bin

# Reboot so the new firmware is loaded
sudo reboot
```

Reconnect after reboot.

---

## Step 2 — Update the system and install dependencies

```bash
sudo apt update
sudo apt full-upgrade -y
sudo apt install -y \
  git libgmp3-dev gawk qpdf bison flex make autoconf libtool texinfo xxd \
  libnl-3-dev libnl-genl-3-dev bc libssl-dev tcpdump
```

---

## Step 3 — Raspberry Pi 5 only: install 32-bit compatibility libraries

> **Skip this if you are on a Raspberry Pi 4.**

The Nexmon build tools include some 32-bit (armhf) binaries. On a 64-bit-only system you need to add 32-bit library support:

```bash
sudo dpkg --add-architecture armhf
sudo apt update
sudo apt install -y \
  libc6:armhf libisl23:armhf libmpfr6:armhf libmpc3:armhf libstdc++6:armhf

# Create symlinks for older library names the build tools expect
sudo ln -s /usr/lib/arm-linux-gnueabihf/libisl.so.23 /usr/lib/arm-linux-gnueabihf/libisl.so.10
sudo ln -s /usr/lib/arm-linux-gnueabihf/libmpfr.so.6 /usr/lib/arm-linux-gnueabihf/libmpfr.so.4
```

---

## Step 4 — Install Python 2.7

One of the Nexmon build tools requires Python 2.7, which is no longer in current Debian repositories. Pull it from the Debian Stretch archive:

```bash
# Temporarily add the old Debian Stretch repo
sudo cp /etc/apt/sources.list /tmp/
echo 'deb http://archive.debian.org/debian/ stretch contrib main non-free' | sudo tee -a /etc/apt/sources.list

sudo apt update
sudo apt install -y python2.7

# Remove the old repo and restore the original sources
sudo mv /tmp/sources.list /etc/apt/sources.list
sudo apt update
```

---

## Step 5 — Clone and build the Nexmon base

```bash
cd ~
git clone --depth=1 https://github.com/seemoo-lab/nexmon.git
cd nexmon

# Set up the build environment variables
source setup_env.sh

# Fix the b43-beautifier script to use Python 2.7
sed -i '1 s/$/2.7/' $NEXMON_ROOT/buildtools/b43-v3/debug/b43-beautifier

# Build the base tools
make
```

> **Note:** `source setup_env.sh` sets environment variables (`$NEXMON_ROOT`, compiler paths, etc.) that the rest of the build depends on. If you open a new terminal later, run `source ~/nexmon/setup_env.sh` again before running any `make` commands.

---

## Step 6 — Build and install nexutil

`nexutil` is the command-line tool you'll use to configure CSI extraction and switch the Wi-Fi interface into monitor mode.

```bash
cd $NEXMON_ROOT/utilities/nexutil

# Build and install (USE_VENDOR_CMD=1 is required — without it the driver rejects commands)
sudo -E make install USE_VENDOR_CMD=1

# Give nexutil permission to manage network interfaces without sudo every time
sudo setcap cap_net_admin+ep /usr/bin/nexutil
```

---

## Step 7 — Clone the Nexmon CSI patch

```bash
cd $NEXMON_ROOT/patches/bcm43455c0/7_45_189
git clone --depth=1 https://github.com/seemoo-lab/nexmon_csi.git
cd nexmon_csi
```

---

## Step 8 — Build and install the patched firmware

This installs the CSI-capable firmware using the system's `update-alternatives` mechanism, which makes it easy to switch back to the default firmware later.

```bash
# Compile and install the patched firmware
make -f Makefile.rpi install-firmware

# Tell NetworkManager to leave the wlan0 interface alone
make -f Makefile.rpi unmanage

# Reload the Wi-Fi driver to apply the new firmware
make -f Makefile.rpi reload-full
```

---

## Step 9 — Start capturing CSI

**Configure the CSI extractor.** Generate your config string with the `makecsiparams` tool (included in the nexmon_csi repo), then apply it:

```bash
nexutil -s500 -b -l34 -v<your-config-string>
```

**Enable monitor mode:**

```bash
nexutil -m1
```

**Capture CSI packets** (they arrive as UDP on port 5500):

```bash
sudo tcpdump -i wlan0 dst port 5500
```

---

## Restoring the default Wi-Fi

To go back to normal Wi-Fi (CSI extraction will stop working):

```bash
# From inside the nexmon_csi directory
make -f Makefile.rpi restore-wifi
```

Or switch firmware manually:

```bash
sudo update-alternatives --config cyfmac43455-sdio.bin
# Then reload the driver:
make -f Makefile.rpi reload-full
```

To restore from the backup you made in Step 1:

```bash
sudo cp ~/brcmfmac43455-sdio.bin.backup /lib/firmware/brcm/brcmfmac43455-sdio.bin
sudo reboot
```

---

## Quick reference — commands you'll use repeatedly

| What | Command |
|---|---|
| Re-activate CSI after reboot | `source ~/nexmon/setup_env.sh` → `nexutil -s500 -b -l34 -v<config>` → `nexutil -m1` |
| Capture packets | `sudo tcpdump -i wlan0 dst port 5500` |
| Reload driver | `make -f Makefile.rpi reload-full` (from nexmon_csi dir) |
| Switch firmware | `sudo update-alternatives --config cyfmac43455-sdio.bin` |
| Restore Wi-Fi | `make -f Makefile.rpi restore-wifi` |
