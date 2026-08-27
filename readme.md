# RPi CSI Human Sensing

WiFi Channel State Information (CSI) based **human presence and activity
detection** on a Raspberry Pi with
[nexmon_csi](https://github.com/seemoo-lab/nexmon_csi) firmware. The system
senses people by how their bodies perturb WiFi propagation — no camera, works in
the dark, works through some occlusion.

📄 **Full documentation:** [ananyasahani.github.io/rpi-csi-pose-sensing](https://ananyasahani.github.io/rpi-csi-pose-sensing/)

> **Note on the name.** The repo is still called `rpi-csi-pose-sensing` for link
> stability. The confirmed scope is *classification* — presence and coarse
> activity — not 3D pose. See [Scope](#scope).

## Goal

A Mamba-based sequence model for (1) binary presence detection and (2) coarse
activity recognition (still / walk / multi-person), using **self-supervised
pretraining** on unlabeled ambient CSI to cut the labeled-data requirement.

The open question it answers: *do the self-supervised gains reported for pose on
high-end multi-antenna hardware hold for simpler tasks on cheap, single-antenna
hardware?*

## Scope

In scope (Phase 1): presence + coarse activity classification (`empty` /
`one_still` / `one_walk`), session-disjoint evaluation, plus a placement study and
a channel study.

Future work, deliberately parked: 3D pose estimation with camera labels,
through-wall sensing, fine-grained multi-person counting, ESP32 hardware. Each is
a phase of its own — see [`context/06-execution-plan.md`](context/06-execution-plan.md).

Because the task is classification, **no camera is needed**: capture runs from a
timed script, and the instruction timing *is* the ground-truth label.

## How it works

A transmitter Pi pings the laptop over WiFi (channel 11), generating over-the-air
frames. A receiver Pi with patched Nexmon firmware, in monitor mode, passively
overhears those frames and computes the channel estimate (CSI) for each. Amplitude
changes in that CSI reveal motion and presence. We window the amplitude stream,
train models to classify each window, and pretrain on unlabeled ambient captures to
improve label efficiency.

## Hardware

| Role | Device | Job |
|---|---|---|
| Receiver (Rx) | Raspberry Pi 4B (`bcm43455c0`) | Nexmon CSI firmware, monitor mode, `tcpdump` |
| Transmitter (Tx) | Raspberry Pi 3 (`bcm43430a1`) | Plain WiFi client; pings the laptop to generate traffic |
| Gateway | Laptop | Internet via phone hotspot, shared to the Rx over Ethernet (ICS) |

Channel 11 / 20 MHz, 64 subcarriers (~52 usable), ~10 Hz sampling, amplitude only.
Full topology and the locked parameter table live in [`CLAUDE.md`](CLAUDE.md).
The four arrangements tried before this one are written up in
[`journey.md`](journey.md).

## Pipeline

```
pcap → parse (nexcsi) → drop null/pilot → amplitude (np.abs) → Hampel despike
     → per-subcarrier z-score (TRAIN stats only) → 2 s windows, 50% overlap
     → tensor (N, 20, 52)
```

## Models (built in this order)

1. Threshold baseline on PC1 variance — no training, the number everything must beat
2. RandomForest / SVM on hand features
3. Small CNN over the window tensor
4. Mamba sequence model
5. **Mamba + masked-reconstruction SSL pretraining** — the headline experiment

## Quickstart

1. **Install firmware** — [`installation.md`](installation.md) (one-time build)
2. **Bring up the rig** — [`context/01-installation-setup.md`](context/01-installation-setup.md) (every session; Nexmon state does not survive reboot)
3. **Capture data** — [`context/02-data-collection.md`](context/02-data-collection.md)
4. **Preprocess** — [`context/03-preprocessing.md`](context/03-preprocessing.md)
5. **Visualize / sanity-check** — [`context/04-ml-visualization.md`](context/04-ml-visualization.md)
6. **Train models** — [`context/05-deep-learning.md`](context/05-deep-learning.md)
7. **Follow the plan** — [`context/06-execution-plan.md`](context/06-execution-plan.md)

## Documentation map

- [`CLAUDE.md`](CLAUDE.md) — standing context: locked parameters, topology,
  rationale, current status. Start here.
- [`context/`](context/) — the planning docs, `01`–`06`, plus
  [`DOCUMENTATION-GUIDE.md`](context/DOCUMENTATION-GUIDE.md) (which file owns
  which fact — read it before editing any doc).
- Published site pages ([ananyasahani.github.io/rpi-csi-pose-sensing](https://ananyasahani.github.io/rpi-csi-pose-sensing/)):
  [`index.md`](index.md) (overview), [`journey.md`](journey.md) (hardware setup
  history), [`installation.md`](installation.md) (firmware build),
  [`csi_preprocessing.md`](csi_preprocessing.md) (CSI theory and capture format),
  [`data-collection.md`](data-collection.md) (dataset protocol),
  [`visualization.md`](visualization.md) (signal characterization),
  [`models.md`](models.md) (models and roadmap). Diagrams and MathJax are wired in
  via [`_includes/head-custom.html`](_includes/head-custom.html).

## Status

Rig confirmed working — real CSI captured over channel 11 with the Tx→laptop ping.
Spectrogram tooling drafted. **Next milestone: the Phase 0 pilot** — one scripted
`empty`/`still`/`walk` session, visualized, to confirm class separability before
bulk collection.

## Team

Ananya Sahani · Sandeep Balaji · Hemesh Kukreja
