# Documentation Guide — for Claude Code

This file explains **how the documentation is organized, what each file owns, and
when/how to update it.** Read this before editing any doc so changes land in the
right place and stay consistent.

## The governing principle

`CLAUDE.md` (repo root) holds **durable, cross-cutting facts and rationale** —
the things true across the whole project. The `context/NN-*.md` files hold the
**detailed, phase-specific content**. When something changes, update the most
specific file that owns it, and update `CLAUDE.md` only if the change is a locked
parameter, a confirmed result, or a scope/goal decision.

## Ownership map — where each kind of fact lives

| If you're changing... | Update this file |
|-----------------------|------------------|
| Project goal, scope, why-we-do-X rationale | `CLAUDE.md` |
| A locked capture parameter (channel, fs, window) | `CLAUDE.md` table + the doc that uses it |
| Firmware / nexmon / environment install steps | `context/01-installation-setup.md` |
| Scenarios, positions, capture protocol, labeling | `context/02-data-collection.md` |
| Preprocessing steps, tensor shapes, leakage rules | `context/03-preprocessing.md` |
| Visualization / clustering / unsupervised methods | `context/04-ml-visualization.md` |
| Model architectures, training, SSL pretraining | `context/05-deep-learning.md` |
| Timeline, experiment list, confirmed results | `context/06-execution-plan.md` |
| One-time firmware build steps (public guide) | `installation.md` (repo root) |
| CSI theory, math, pcap payload format | `csi_preprocessing.md` (repo root) |
| Hardware/OS troubleshooting history | `journey.md` (repo root) |
| Project front page / site landing page | `readme.md` / `index.md` (repo root) |

The repo root also holds the **published GitHub Pages site** (`index.md`,
`installation.md`, `csi_preprocessing.md`, `journey.md`, driven by `_config.yml`).
Those pages are the outward-facing story; `context/` is the internal working plan.
When a fact changes in both, change it in the owning file first and keep the site
page's version short, linking here rather than restating detail — the site is
where duplicated numbers drift worst, because nobody re-reads it.

## Rules for updating

1. **One fact, one home.** Don't duplicate a parameter value across files. State
   it in `CLAUDE.md`'s locked table and *reference* it elsewhere ("channel 11, see
   CLAUDE.md"). Duplicated numbers drift out of sync — the top failure mode.
2. **Rationale travels with the fact.** When you add or change a decision, write
   *why* in one sentence. A doc that says "window = 2 s" is weaker than one that
   says "window = 2 s (motion shows as variance over ~1–2 s, not per-packet)."
3. **Confirmed results go in `context/06-execution-plan.md`**, with the date and the exact
   setup that produced them (model, split, data amount). Never overwrite a prior
   result — append; the trajectory matters.
4. **Keep `CLAUDE.md`'s "Current status" current.** One line per meaningful update,
   newest first. This is how a fresh session knows where things stand.
5. **Flag parameter changes loudly.** If a locked capture parameter changes, note
   it AND note that data captured before the change may be incompatible. Silent
   parameter drift is how a dataset becomes unusable.
6. **Preserve scope discipline.** If asked to add pose estimation, camera labels,
   ESP32, or through-wall work, add it under an explicit "Future work / Phase N"
   heading — do not fold it into the core in-room classification plan. The core
   staying small is a deliberate design choice (see `06-execution-plan.md`).

## Style

- Prose and short tables. Avoid deep bullet nesting.
- Every doc opens with a one-paragraph "What this covers / why it matters."
- Commands in fenced blocks, copy-pasteable, with the machine they run on stated
  (receiver Pi / transmitter Pi / laptop).
- When you add a command, say what success looks like ("you should see packets
  scroll" / "prints (N, 20, 52)").

## When unsure

If a requested change is ambiguous about which file owns it, or would contradict a
locked parameter or the project scope, ask the human before editing rather than
guessing. A wrong edit to shared context propagates to every future session.
