# 01 — Installation & Setup

**What this covers / why it matters:** Everything needed to go from bare hardware
to a receiver Pi that produces CSI you can capture. The Nexmon setup is stateful
and does not survive reboots, so this doubles as the "bring it back up" checklist
every session.

## Hardware roles (recap)

- **Receiver Pi (Pi 4):** Nexmon patched firmware, WiFi in monitor mode, captures.
- **Transmitter Pi (Pi 3):** ordinary WiFi client, pings the laptop for traffic.
- **Laptop:** internet via phone hotspot; shares to receiver over Ethernet (ICS).

See `CLAUDE.md` for the full topology and why the signal path is what it is.

## Part A — One-time software install (receiver Pi)

The Nexmon CSI firmware patch must be built and installed once. Follow the
official `seemoo-lab/nexmon_csi` getting-started guide for the Pi's kernel version.
After that, the patched firmware is registered with `update-alternatives`, so
switching between stock and CSI firmware is a selection, not a rebuild.

Key requirements learned the hard way:
- `nexutil` must be compiled with `USE_VENDOR_CMD=1`, or the driver rejects the
  IOCTLs that configure the extractor.
- The tools `makecsiparams` and `nexutil` may not be on `PATH`. They live under the
  `nexmon_csi` tree (e.g. `utils/makecsiparams/makecsiparams`) and the nexmon
  `utilities/nexutil/`. Call by full path or add to `PATH`.

Confirm the CSI firmware is the active alternative:
```bash
sudo update-alternatives --config cyfmac43455-sdio.bin
# select the entry under .../nexmon/... (marked *). Press Enter to keep it.
```

## Part B — Python environments (laptop / analysis machine)

`nexcsi` pins `numpy<2.0`; scikit-learn / scipy / umap want numpy 2.x. Keep them
apart:

```bash
# Parsing env (numpy 1.x) — only decodes pcaps to .npy
python3 -m venv .venv-parse
. .venv-parse/bin/activate
pip install "numpy<2.0" nexcsi
deactivate

# Main env (numpy 2.x) — everything else
python3 -m venv .venv
. .venv/bin/activate
pip install numpy scipy scikit-learn matplotlib umap-learn torch
```

Alternative if you'd rather stay single-env on numpy 1.x:
```bash
pip install nexcsi --no-deps     # ignore its over-cautious numpy pin
```

Sanity check the main env (scipy/numpy ABI mismatch has bitten this project):
```bash
python -c "from scipy.signal import spectrogram; import umap, sklearn; print('ok')"
```
If that errors, `pip install --force-reinstall numpy scipy`.

## Part C — Per-session bring-up (receiver Pi)

Nexmon runtime state (`nexutil` config + monitor mode) is wiped by reboot even
though the firmware *selection* persists. Re-run this every session.

```bash
# 0. WiFi may be RF-killed / down after boot
sudo rfkill unblock all
sudo ip link set wlan0 up

# 1. generate config for channel 11 / 20 MHz, filtered to the transmitter's MAC
cd ~/nexmon/patches/bcm43455c0/7_45_189/nexmon_csi
./utils/makecsiparams/makecsiparams -c 11/20 -C 1 -N 1 -m <TRANSMITTER_WIFI_MAC>
#   -> copy the printed base64 string

# 2. load config into firmware
sudo nexutil -Iwlan0 -s500 -b -l34 -v<BASE64_STRING>

# 3. enable monitor mode
sudo nexutil -Iwlan0 -m1

# 4. verify — must print "monitor: 1" (do NOT trust iwconfig here)
sudo nexutil -Iwlan0 -m
```

Get the transmitter's WiFi MAC (on the transmitter Pi): `ip link show wlan0` →
the `link/ether` line. Filtering to it means every CSI sample comes from one known
source — cleaner data, reproducible.

## Part D — Start traffic (transmitter Pi)

The transmitter must be associated to the phone hotspot (channel 11) so its pings
go over the air where the receiver can hear them. Confirm, then ping:
```bash
iw dev wlan0 link                     # should show SSID = your hotspot
ping -i 0.1 <LAPTOP_HOTSPOT_IP>       # ~10 Hz; the sampling rate of the dataset
```
`ping -i` below 0.2 s needs `sudo`. Whatever rate you pick, keep it identical
across all sessions (it IS the CSI sample rate `fs`).

## Part E — Confirm CSI is flowing (receiver Pi)

```bash
sudo tcpdump -i wlan0 dst port 5500        # watch live; packets should scroll
```
If silent, run `sudo tcpdump -i wlan0` (all traffic):
- traffic scrolls but nothing on port 5500 → nexutil config didn't take (redo C)
- total silence → no channel-11 frames reaching the radio (check D: is the
  transmitter really on channel 11? is the hotspot on channel 11? `netsh wlan show
  interfaces` on the laptop shows the channel).

## Part F — Restore stock WiFi (when done sensing)

```bash
cd ~/nexmon/.../nexmon_csi
make -f Makefile.rpi restore-wifi     # reverts firmware; normal WiFi returns
```
If `make` errors with "recipe commences before first target", the Makefile has
Windows line endings — `dos2unix Makefile.rpi` — or just reselect stock firmware
via `update-alternatives` and reload the driver
(`sudo modprobe -r brcmfmac && sudo modprobe brcmfmac`).

## Troubleshooting quick table

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| `device is not up` | RF-kill / iface down | `rfkill unblock all; ip link set wlan0 up` |
| `monitor: 0` after `-m1` | config didn't load | redo Part C in order |
| 0 packets on port 5500 | no ch-11 traffic OR config lost | Part E diagnostic |
| `makecsiparams: not found` | not on PATH | call by full path under `utils/` |
| capture goes sparse mid-session | hotspot channel hopped | recheck laptop channel, re-config |
| scipy import crash | numpy/scipy ABI mismatch | `pip install --force-reinstall numpy scipy` |
