

# CSI Fundamentals & Data Processing

This page covers the theory behind Channel State Information (CSI), how it is
captured with `nexmon_csi`, and the preprocessing and visualization pipeline
used in this project.

- [What is CSI?](#what-is-csi)
- [The Math Behind CSI](#the-math-behind-csi)
- [nexmon_csi Capture Format](#nexmon_csi-capture-format)
- [Preprocessing Pipeline](#preprocessing-pipeline)
- [Visualization](#visualization)
- [Important Commands](#important-commands)

---

## What is CSI?

Channel State Information describes how a wireless signal is altered as it
travels from transmitter to receiver — the combined effect of scattering,
fading, and power decay caused by multipath propagation. Unlike RSSI, which
gives a single scalar per packet, CSI is a fine-grained, per-subcarrier
measurement of the wireless channel, making it useful for applications like
localization, motion/gesture sensing, and human activity recognition.

In an OFDM system (802.11a/g/n/ac), the channel is divided into many narrow
orthogonal subcarriers. CSI is the estimated channel response for *each*
subcarrier, for *each* transmit–receive antenna pair, giving both amplitude
and phase information rather than just signal strength.

---

## The Math Behind CSI

### OFDM signal model

For a single subcarrier `k`, the frequency-domain received signal relates to
the transmitted signal through the channel:

```
Y(k) = H(k) · X(k) + N(k)
```

- `X(k)` — transmitted symbol on subcarrier k
- `Y(k)` — received symbol on subcarrier k
- `H(k)` — channel frequency response (this is the CSI)
- `N(k)` — additive noise

Since the transmitted symbol is known (from preamble/training fields), the
receiver estimates CSI as:

```
H(k) = Y(k) / X(k)
```

### Complex representation

`H(k)` is a complex number, so it carries both magnitude and phase:

```
H(k) = |H(k)| · e^(jθ(k))
```

- **Amplitude (magnitude):** `|H(k)| = sqrt(Re(H(k))² + Im(H(k))²)`
- **Phase:** `θ(k) = atan2(Im(H(k)), Re(H(k)))`

Amplitude tells you how much a subcarrier's signal was attenuated; phase
tells you how much it was delayed/shifted. Both vary over time as the
environment changes (e.g., a person moving through the signal path).

### MIMO / multi-dimensional CSI

With multiple antennas and multiple packets over time, CSI becomes a tensor:

```
H[t, tx, rx, k]
```

indexed by time, transmit antenna, receive antenna, and subcarrier. Most
consumer chips supported by `nexmon_csi` (used on a Raspberry Pi, for
example) expose 1 transmit stream and 1–4 receive antennas, so in practice
you'll usually work with a `[time, subcarrier]` amplitude/phase matrix per
antenna/core.

### Subcarrier counts by bandwidth

`nexmon_csi` reports CSI for every subcarrier in the configured channel
bandwidth, including null and pilot subcarriers that must be excluded during
preprocessing:

| Bandwidth | Total subcarriers | Notes |
|---|---|---|
| 20 MHz | 64 | fewer null/pilot to strip |
| 40 MHz | 128 | ~14 null, 6 pilot |
| 80 MHz | 256 | most commonly used for finer resolution |

---

## nexmon_csi Capture Format

`nexmon_csi` patches the Wi-Fi firmware so that every matching frame's CSI is
pushed out as a **UDP packet** (source `10.10.10.10`, destined to
`255.255.255.255`, port `5500`), which you capture into a `.pcap` file. Each
packet payload contains, in order: magic bytes, RSSI, frame-control byte,
source MAC, sequence number, core/spatial-stream and chanspec fields, chip
version, and finally the raw CSI samples as **interleaved Int16 real/imaginary
pairs** (one complex value per subcarrier).

A Python decoder (e.g. `nexcsi`) reads this directly into a structured NumPy
array, exposing fields like `rssi`, `fctl`, `mac`, `seq`, and `csi`.

---

## Preprocessing Pipeline

1. **Capture** raw CSI as a `.pcap` file with `tcpdump` while the firmware is
   configured with `nexutil`/`makecsiparams`.
2. **Parse** the pcap into a structured array (`nexcsi`, `csiread`, or
   `CSIKit`), pulling out the raw Int16 CSI payload per packet.
3. **Reconstruct complex CSI** by pairing each interleaved (real, imag) pair
   into a complex number per subcarrier: `H = real + 1j*imag`.
4. **Strip null and pilot subcarriers** — these carry no usable channel
   information and will otherwise show up as zeros/outliers in your matrix.
5. **Extract amplitude and phase** per subcarrier, per packet, using the
   formulas above.
6. **Unwrap and sanitize phase** — raw phase wraps at ±π and includes a
   random timing/frequency offset per packet. Use `np.unwrap()` across
   subcarriers, then remove the linear phase trend (packet detection delay)
   with a linear fit/regression subtraction so only the true channel phase
   remains.
7. **Remove outliers** in the amplitude stream — a Hampel filter or rolling
   median filter works well for the occasional corrupted packet/spike.
8. **Denoise / smooth** — a low-pass (e.g., Butterworth) filter across time,
   or PCA across subcarriers, reduces high-frequency noise while preserving
   the motion/activity signal of interest.
9. **Normalize** amplitude (e.g., min-max or z-score per subcarrier) if the
   data will feed into a machine-learning model.

---

## Visualization

The two standard views for inspecting CSI data:

- **Amplitude heatmap** — time on the x-axis, subcarrier index on the
  y-axis, color intensity as amplitude. This is the fastest way to spot
  motion events or capture issues.
- **Phase plot** — sanitized phase per subcarrier over time, usually plotted
  as line traces for a handful of subcarriers rather than a full heatmap.

```python
import matplotlib.pyplot as plt

# amplitude: shape [n_packets, n_subcarriers]
plt.imshow(amplitude.T, aspect="auto", cmap="viridis",
           extent=[0, amplitude.shape[0], 0, amplitude.shape[1]])
plt.xlabel("Packet index (time)")
plt.ylabel("Subcarrier index")
plt.colorbar(label="Amplitude")
plt.title("CSI Amplitude Heatmap")
plt.show()
```

`CSIKit` also ships built-in heatmap/plotting utilities if you'd rather not
write the matplotlib boilerplate yourself.

> If you want the math rendered nicely (not just as code blocks), enable
> MathJax in `_config.yml` / a head include — plain GitHub Pages Markdown
> does not render LaTeX by default.

---

## Important Commands

### Build & install nexmon_csi

```bash
cd utilities/nexutil/
make && make install

# from the nexmon_csi patch directory
make install-firmware
```

### Generate CSI extraction parameters

```bash
# Example: channel 157, 80 MHz bandwidth, core 0, spatial stream 0
mcp -c 157/80 -C 1 -N 1

# Full option list
mcp -h
```

### Configure the firmware extractor (bcm43455c0 / Pi-class chips)

```bash
pkill wpa_supplicant
ifconfig wlan0 up
nexutil -Iwlan0 -s500 -b -l34 -v<base64-params-from-mcp>
```

### Put the interface in monitor mode

```bash
iw phy "$(iw dev wlan0 info | gawk '/wiphy/ {printf "phy" $2}')" \
  interface add mon0 type monitor
ifconfig mon0 up
```

### Capture CSI to a pcap file

```bash
# Live view
tcpdump -i wlan0 dst port 5500

# Save N packets to disk
tcpdump -i wlan0 dst port 5500 -vv -w output.pcap -c 1000
```

### Decode captured CSI in Python

```bash
pip install nexcsi
```

```python
from nexcsi import decoder

device = "raspberrypi"  # or: nexus5, nexus6p, rtac86u
samples = decoder(device).read_pcap("output.pcap")

csi = decoder(device).unpack(samples["csi"])   # complex64 array
rssi = samples["rssi"]
```

---

*Next: see the [Installation](./installation.md) page for full environment
setup, or [Data Format](./data-format.md) for a deeper breakdown of the pcap
payload layout.*
