# CLAUDE.md — Project Context for Claude Code

> This file is standing context for Claude Code. It is read at the start of every
> session. Treat it as the single source of truth for **what this project is**,
> **what is already decided**, and **what is still unconfirmed**. When a decision
> is settled in a session, UPDATE THIS FILE (see §7, "How to maintain this file").

---

## 1. What this project is

WiFi **Channel State Information (CSI)** based human sensing on commodity hardware.
A Raspberry Pi with patched Nexmon firmware passively captures CSI from Wi-Fi
frames; changes in the signal caused by human presence and motion are used to
detect **presence** and classify **coarse activity** (empty / still / walk).

The end goal is a **Mamba-based sequence model** with **self-supervised
pretraining** on unlabelled ambient CSI, fine-tuned on a small labelled set.
Simpler baselines (threshold, RandomForest, CNN) come first and must exist before
the Mamba work.

**Scope discipline:** the confirmed, in-scope task is *classification*
(presence + coarse activity). Pose estimation, through-wall sensing, multi-person
counting beyond a coarse level, and ESP32 hardware are **future work** (see
`context/06-execution-plan.md`), NOT part of the first deliverable. Do not
generate code or docs that assume those unless explicitly asked. The repository
name (`rpi-csi-pose-sensing`) and the published site URL are historical — they
predate this scope decision and are kept only so existing links keep working.

## 2. Hardware & network topology (CONFIRMED)

- **Receiver Pi (Rx, Pi 4)** = the sensor. Runs patched Nexmon firmware, monitor
  mode, `tcpdump`. Senses via its **Wi-Fi radio in monitor mode on channel 11**.
  Connected to the laptop by **Ethernet** — this Ethernet link is ONLY for
  delivering captured CSI and internet (via ICS), NOT the sensing path.
- **Transmitter Pi (Tx, Pi 3)** = traffic source. A plain Wi-Fi client associated
  to the phone hotspot. Continuously pings the laptop to generate over-the-air
  frames. Located ~3–4 m from the Rx.
- **Laptop** = network gateway/target. Internet via phone hotspot; shares it to the
  Rx Pi over Ethernet (Windows ICS, `192.168.137.x` subnet).
- **Phone** = hotspot ("Galaxy"), next to the laptop.

**Sensing signal path:** Tx Pi → (Wi-Fi, channel 11) → hotspot/laptop, and the
Rx Pi's Wi-Fi radio **passively overhears** those frames. If the Tx's ping ever
travels over a path the Rx is not listening on, captures will be empty.

How this topology was arrived at (four failed arrangements before it) is recorded
in `journey.md`.

## 3. Capture parameters (CONFIRMED unless noted)

| Parameter | Value | Note |
|-----------|-------|------|
| Channel / bandwidth | 11 / 20 MHz | Fixed. Must match hotspot channel. |
| Subcarriers | 64 (~52 usable) | Set by bandwidth; drop null/pilot. |
| Sampling rate | ~10 Hz (`ping -i 0.1`) | Keep IDENTICAL across all sessions. |
| Signal used | Amplitude only | Phase is unreliable on this chip. |
| MAC filter | Tx Pi's Wi-Fi MAC | `makecsiparams -m` → clean single-source CSI. |
| Window | 2 s (20 packets), 50% overlap | Tensor `(N, 20, 52)`. |

**UNCONFIRMED / verify before relying on:** exact usable-subcarrier indices for
this chip; whether the Phase 0 pilot shows empty vs walk actually separate.

## 4. Key technical facts (learned, do not re-derive wrongly)

- CSI is delivered as **fabricated UDP packets on port 5500**. `tcpdump` labels
  them link-type "Ethernet" — this is an artifact of Nexmon's delivery mechanism,
  NOT physical Ethernet. The CSI inside is real over-the-air channel data.
- **AGC** (automatic gain control) causes amplitude spikes that look like motion
  but are not → remove with a Hampel filter in preprocessing.
- **nexcsi pins numpy<2.0.** Either use a separate numpy-1.x env for parsing, or
  `pip install nexcsi --no-deps`. Do not fight this by downgrading the whole env.
- Nexmon runtime config (`nexutil -m1`, `-s500 ... -v<cfg>`) does NOT survive a
  reboot; the firmware *selection* (`update-alternatives`) does. Re-run the
  nexutil sequence after any reboot. See `context/01-installation-setup.md`.
- Patching the firmware drops `wlan0`, so a wireless SSH session dies the moment
  monitor mode is enabled. Always have a wired or standalone path to the Pi.

## 5. Repository layout

```
CLAUDE.md                      ← this file (standing context, canonical)
readme.md                      ← GitHub front page
index.md, installation.md,     ← published site (GitHub Pages, _config.yml)
  csi_preprocessing.md,
  journey.md
context/
  README.md                    ← index of the planning docs
  DOCUMENTATION-GUIDE.md       ← which file owns which fact; read before editing docs
  01-installation-setup.md     ← install + firmware + per-session rig bring-up
  02-data-collection.md        ← scenarios, positions, labelling protocol
  03-preprocessing.md          ← preprocessing steps + rationale + leakage rules
  04-ml-visualization.md       ← EDA / unsupervised inference plan
  05-deep-learning.md          ← CNN + Mamba + SSL plan
  06-execution-plan.md         ← phases, experiments, confirmed-results log
notebooks/
  spectrogram.py               ← pcap → amplitude spectrogram
  lstm.ipynb, model.ipynb      ← early model experiments
  datasets/                    ← own captures (.pcap), spectrogram scripts, spectrograms/
  dataset-HAR-ORT/             ← external reference dataset (HAR-ORT pcaps)
plots/                         ← generated figures
visualize_csi.py, download.py  ← public UT-HAR dataset exploration
shell_scripts/activate.sh      ← venv helper
```

## 6. Conventions (enforce in any code you write)

- **No test-set leakage.** Normalisation stats computed on TRAIN only.
- **Session-disjoint splits.** Never split train/test by random window; hold out
  whole sessions, and ≥1 day and ≥1 person.
- **Filenames:** `{class}_{day}_{person}_{index}.pcap`
  e.g. `one_walk_day2_personA_003.pcap`.
- Amplitude-only unless a task explicitly needs phase.
- Fixed window = 2 s (~20 packets at 10 Hz), 50% overlap, tensor `(N, 20, 52)`.
- Preprocessing order is fixed; see `context/03-preprocessing.md`.

## 7. How to maintain this file

When you (Claude Code) change project state, keep this file current:
- A parameter gets **confirmed** → move it out of "UNCONFIRMED" and state the value.
- A **decision** is made (final window size, channel, model choice) → record it here
  with a one-line reason.
- A new doc is added under `context/` → add it to the layout in §5.
- Never delete the rationale ("why"); future sessions rely on it.
- If asked to update docs, first re-read `context/DOCUMENTATION-GUIDE.md` and the
  relevant `context/*.md`, THEN edit, and reflect any cross-cutting change back here.

**Do not** invent hardware details, accuracy numbers, or dataset sizes. If a fact
is not in this file or the docs, say it is unknown rather than guessing.

## 8. Current status (newest first)

- Documentation reconciled with the classification scope; site pages and README no
  longer describe the project as pose estimation.
- Spectrogram tooling (live + file-based) drafted; external HAR-ORT pcaps pulled in
  as a reference dataset.
- Rig confirmed working: channel 11, transmitter→laptop ping, real CSI captured.
- **Next:** Phase 0 pilot — one scripted empty/still/walk session, run through
  preprocessing and the four-plot visualisation, to confirm class separability
  before bulk collection. See `context/06-execution-plan.md`.
