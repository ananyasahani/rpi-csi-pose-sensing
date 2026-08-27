# Planning Docs — RPi CSI Human Sensing

This folder holds the project's working documentation: the detailed, phase-specific
plans behind the WiFi CSI human-sensing system. The repository front page is
[`../readme.md`](../readme.md), and the durable, cross-cutting facts — locked
capture parameters, topology, scope, current status — live in
[`../CLAUDE.md`](../CLAUDE.md).

**Read [`DOCUMENTATION-GUIDE.md`](DOCUMENTATION-GUIDE.md) before editing anything
here.** It says which file owns which kind of fact, and the rules that keep the
docs from drifting out of sync.

## The docs, in the order you'd use them

1. [`01-installation-setup.md`](01-installation-setup.md) — firmware install,
   Python environments, and the per-session rig bring-up checklist (Nexmon's
   runtime state does not survive a reboot, so this is a recurring step).
2. [`02-data-collection.md`](02-data-collection.md) — scenarios, Tx/Rx placement,
   the scripted-session labeling method, and the session-disjoint split rule.
3. [`03-preprocessing.md`](03-preprocessing.md) — the fixed pcap → tensor
   pipeline, step by step, with the leakage rules.
4. [`04-ml-visualization.md`](04-ml-visualization.md) — the four-plot sanity
   sequence, how to tell a person from an AGC artifact, and label-free detectors.
5. [`05-deep-learning.md`](05-deep-learning.md) — threshold → RandomForest → CNN
   → Mamba → Mamba with self-supervised pretraining, and the experiments that
   make it a paper.
6. [`06-execution-plan.md`](06-execution-plan.md) — the phase plan, the idea
   parking lot, and the append-only confirmed-results log.

## Where everything else lives

| You want... | Go to |
|---|---|
| Locked parameters, topology, scope, status | [`../CLAUDE.md`](../CLAUDE.md) |
| Project front page / quickstart | [`../readme.md`](../readme.md) |
| One-time nexmon_csi firmware build | [`../installation.md`](../installation.md) |
| CSI theory, the math, the pcap payload format | [`../csi_preprocessing.md`](../csi_preprocessing.md) |
| Why the hardware is arranged this way | [`../journey.md`](../journey.md) |

## The short version of the project

A transmitter Pi pings the laptop over WiFi on channel 11, generating
over-the-air frames. A receiver Pi with patched Nexmon firmware, in monitor mode,
passively overhears them and computes CSI. Amplitude changes in that CSI reveal
presence and motion. We window the amplitude stream, classify each window as
`empty` / `one_still` / `one_walk`, and pretrain on unlabeled ambient captures to
cut how much labeled data the classifier needs.

This is **classification, not 3D pose** — the label is the scripted activity, so
no camera is needed. Pose, through-wall sensing, fine-grained people-counting and
ESP32 hardware are all deferred; see the parking lot in
[`06-execution-plan.md`](06-execution-plan.md).

## Status

Rig confirmed working (real CSI captured). Next milestone: the Phase 0 pilot — one
scripted `empty`/`still`/`walk` session, visualized, to confirm class separability
before bulk collection.
