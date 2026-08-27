# 02 — Data Collection

**What this covers / why it matters:** How to capture a clean, labeled, generalizable
dataset. Custom data means we own the labels — and sloppy labeling is the top way
WiFi-sensing projects fail. The method here makes labels automatic and the splits
honest.

## Why no camera is needed

We do **classification**, not pose estimation. The label is a category ("walk"),
and we control what happens during capture. If a script says "walk for 60 s," every
packet in that block is labeled `walk` by construction — the instruction timing IS
the ground truth. A camera would only be needed to recover *joint positions* (pose),
which is out of scope. See `CLAUDE.md` scope note.

## Labeling method: scripted timed sessions

Run a capture script that announces each block (countdown / beep), then captures a
fixed duration, saving one cleanly-named pcap per block. You comply with the
instruction; the block's label is fixed. Reproducible, no manual annotation.

Filename convention: `{class}_{day}_{person}_{idx}.pcap`
e.g. `one_walk_day2_p1_003.pcap`. This encodes the label AND the session/day/person
needed for honest splits.

## Test scenarios (by tier — do them in order)

**Tier 1 — core, most reliable (collect and validate first):**
- `empty` — nobody in the room (and remove stray phones/people from the doorway)
- `one_still` — one person seated/standing motionless in the sensing zone
- `one_walk` — one person walking continuously along the Tx–Rx line

**Tier 2 — multi-person (only after Tier 1 clearly separates):**
- `two_still`, `two_walk` — two people
- `three_still`, `three_walk` — three people

**Tier 3 — exploratory (report honestly; don't stake the project on these):**
- `fall` — one person falling onto a mat
- `mixed` — realistic occupancy, e.g. one walking + one still

**Reality check on people-counting:** distinguishing 2 vs 3 people on
single-antenna 20 MHz CSI is genuinely hard (more people = more variance, but the
mapping isn't clean). Frame the solid contribution as presence + coarse activity
(empty/still/walk); treat counting as an exploratory extension.

## Optimal Tx/Rx positions

Grounded in the physics: the direct Tx–Rx path dominates, and a body perturbs the
signal most when it crosses the Fresnel zones around that direct line.

**Canonical placement (use for the main dataset):**
- Tx–Rx **3 m apart** (3–4 m range is fine)
- Both at **torso height (~1–1.3 m)** on stands — NOT on the floor (floor level
  weakens the body reflection)
- **Clear line of sight** between them; **activity area on/near that line**
- **Floor-tape both positions**; identical every session (placement drift silently
  corrupts the dataset)

**Topology constraint:** the transmitter Pi must stay associated to the hotspot to
keep pinging, so its placement is bounded by hotspot range. If you push distance and
captures thin out, check `iw dev wlan0 link` on the transmitter before blaming
placement.

## Vary across sessions (NOT within a block)

Generalization comes from variation *between* sessions:
- different **days / times of day** (multipath drifts)
- different **people** (even 2–3 helps a lot)
- different **still-positions** and **walk-paths**
- capture `empty` **every session** — the empty-room fingerprint drifts, so you
  need empties from every condition, not one canonical empty

## Per-session structure

Cycle the classes in ~60 s blocks, varying order across sessions. Example 10-min
session: empty → one_still → one_walk → empty → one_walk → one_still → ...

At 10 Hz, 60 s ≈ 600 packets/block. With 2 s / 50%-overlap windows that's ~59
labeled windows per block.

## How much data

- **Labeled:** 15–25 sessions, ≥3 days, ≥2 people. ~20 sessions × ~6 blocks × ~59
  windows ≈ **~7,000 labeled windows**. Modest, but the SSL pretraining compensates.
- **Unlabeled (for pretraining):** several long (10–30 min) passive recordings of
  the room in normal use. Collect generously — it's free and it's what the
  self-supervised phase feeds on.

## The rule that makes results trustworthy: session-disjoint splits

Never split train/test by random window — windows from the same session are nearly
identical and leak. Split by **whole session**, and hold out **≥1 day and ≥1 person
never seen in training**. This mirrors the leave-one-environment-out / subject-disjoint
protocols used by the strongest papers in this area. It is non-negotiable; a random
split produces inflated, meaningless accuracy.

## Placement / channel study (a self-contained experiment)

Two cheap, publishable sub-studies that need no new labeling machinery:
- **Placement:** run only `empty` vs `one_walk` across distances (2/3/4/5 m),
  heights (floor/torso/high), and person-position (on-line / 1 m off / far corner).
  Measure detection accuracy → "optimal geometry" result.
- **Channel:** scan channels for interference, pick low-traffic ones, compare
  capture stability and accuracy → "channel selection guidance" result.

Run the **full scenario list at the one canonical placement** (main dataset), and
only the two-class `empty`/`walk` across placements/channels (study). This keeps the
study from exploding into hundreds of sessions.

## Week 0 pilot (do this before bulk collection)

Capture ONE scripted session (empty/still/walk), run it through preprocessing and
the four-plot visualization (see `04-ml-visualization.md`), and confirm the classes
visibly separate on your hardware in your room. If empty vs walk don't separate,
fix the rig before collecting 20 unusable sessions. This single check saves weeks.
