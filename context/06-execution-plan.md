# 06 — Execution Plan

**What this covers / why it matters:** The staged plan that keeps the project from
sprawling. There are many good ideas (through-wall, ESP32, camera-pose, multi-person,
channel/placement studies); the failure mode is doing all of them and finishing none.
This file sequences them and logs confirmed results. The strongest papers each do
ONE clean thing well — so does Phase 1.

## Phase 0 — Pilot (gate everything on this)

**Goal:** confirm the modality works on this hardware in this room before bulk work.
- Bring up the rig (`01`), start traffic, capture ONE scripted session
  (empty/still/walk).
- Run the four-plot visualization (`04`). Confirm `empty` vs `walk` visibly separate.
- **Gate:** if they don't separate, fix the rig (placement, channel, traffic) before
  anything else. Do not collect 20 sessions of unusable data.

## Phase 1 — The foundation paper (do this fully first)

**One-sentence scope:** commodity single-antenna WiFi CSI for presence + coarse
activity recognition, with self-supervised Mamba pretraining from unlabeled ambient
data, evaluated with session-disjoint splits on accessible hardware — plus placement
and channel studies.

**Why this scope:** it's achievable on a Pi + Colab T4, uses data we can actually
collect (no camera), applies the best ideas from RePos/WiFi-JEPA/LightPoseNet, and
answers a real open question: *do the SSL gains shown for pose on high-end hardware
hold for simpler tasks on cheap single-antenna hardware?*

Steps:
1. **Collect** 15–25 labeled sessions + ambient unlabeled, per `02`.
2. **Preprocess** to tensors with session-disjoint splits, per `03`.
3. **Baselines** — threshold, RandomForest, CNN (`05`).
4. **Mamba + SSL** — from-scratch vs. pretrained; label-efficiency curve; masking
   ablation (`05`).
5. **Fold in the placement study and channel study** (`02`) — cheap, no new
   labeling, and they make the paper more rigorous ("we also characterize optimal
   geometry and channel selection").
6. **Write up**, using the three reference papers as structural templates.

## Phase 2 — Pick ONE extension (only after Phase 1 works)

- **Through-wall robustness** — Tx/Rx on opposite sides of a wall, swap inside/outside.
  Great result if it survives; honest negative if it doesn't. High collection cost
  (every condition × geometry). Validate in-room first.
- **Multi-person counting** — 2 vs 3 people, reported honestly as exploratory.
- **Camera-labeled pose** — moves toward the reference papers' task. Expensive:
  needs tight CSI↔camera time-sync, a camera pose model (its errors become label
  noise), person always in view, and only 2D/noisy-3D labels from a single camera.
  A whole phase, not a side task.

## Phase 3 / separate project — hardware-constrained

- **ESP32 as transmitter**, fewer subcarriers, different toolchain/format. Distinct
  enough to stand alone; do NOT blend into the Pi pipeline (it reintroduces the exact
  dimensional-mismatch problem going custom avoided).

## Idea parking lot (captured so they're not lost)

Everything not in Phase 1 lives here until promoted, deliberately kept out of the
core: through-wall, dual-geometry inside/outside swap, camera→skeleton pose labels,
ESP32 constrained hardware, multi-person counting, per-setup architecture variants.
Each is defensible; all together is several years / several papers.

## Confirmed results log (append-only)

> Record every confirmed number here with date + exact setup (model, split, data
> amount). Never overwrite — the trajectory matters. Empty until Phase 1 produces
> results.

| Date | Experiment | Setup (model / split / data) | Metric | Value |
|------|-----------|------------------------------|--------|-------|
| —    | —         | —                            | —      | —     |

## Status snapshot

> Mirror the newest line into `CLAUDE.md`'s "Current status".

- Rig confirmed working (channel 11, transmitter→laptop ping, real CSI captured).
- Spectrogram tooling (live + file-based) drafted.
- **Next:** Phase 0 pilot — scripted empty/still/walk session, visualized.
