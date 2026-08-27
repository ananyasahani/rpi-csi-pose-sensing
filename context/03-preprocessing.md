# 03 — Preprocessing

**What this covers / why it matters:** The fixed pipeline that turns raw pcaps into
a labeled tensor dataset. It must be identical for every file and must never leak
test statistics into training. Get this wrong and every downstream number is
meaningless.

## The pipeline (fixed order)

```
pcap
 └─ 1. parse → complex CSI array           (nexcsi, numpy-1.x env)
 └─ 2. drop null/pilot subcarriers          (~64 → ~52 usable)
 └─ 3. amplitude = np.abs(csi)              (phase is unreliable on this chip)
 └─ 4. Hampel despike per subcarrier        (kills AGC amplitude jumps)
 └─ 5. z-score per subcarrier               (stats from TRAIN ONLY)
 └─ 6. window: 2 s, 50% overlap             (motion = variance over ~1–2 s)
 └─ 7. stack → tensor (N, T, C) e.g. (N, 20, 52)
```

## Step notes and rationale

**1. Parse.** Use `nexcsi` in the numpy-1.x env to decode `samples['csi']` and
`unpack` to complex. Save intermediate `.npy` so the rest of the pipeline runs in
the numpy-2.x env without touching nexcsi again. Some rows may be malformed —
sanity-check length/RSSI and drop bad rows.

**2. Drop null/pilot subcarriers.** These carry arbitrary values, not channel
information. `nexcsi` exposes which indices are null/pilot; remove those columns.

**3. Amplitude only.** `np.abs`. Phase carries a random per-boot offset on this
hardware and is not usable without calibration we don't have.

**4. Hampel despike.** The WiFi chip's AGC rescales the signal, creating sharp
amplitude spikes that look like activity but aren't. A Hampel (median +
MAD-threshold) filter per subcarrier removes them. This is the single most important
cleaning step for this hardware.

**5. Normalization — the leakage rule.** Per-subcarrier z-score. Compute mean/std
**on the training split only**, then apply those same stats to val/test. Computing
stats over the whole dataset (or per-file) leaks test information and inflates
results. This is the most common silent bug — guard it.

**6. Windowing.** Presence/motion shows up as *variance over time*, not in any
single packet, so we classify windows, not packets. 2 s at 10 Hz = 20 packets/window;
50% overlap for more training examples. Window length and rate are locked
parameters (see `CLAUDE.md`).

**7. Tensor shape.** `(n_windows, window_len, n_subcarriers)`, e.g. `(N, 20, 52)`.
This is the model input. Label per window = the source block's class (from the
filename).

## Splitting (must happen at the FILE/SESSION level)

Do the train/val/test split **before** windowing, by whole session — assign entire
sessions to a split, then window within each split. Hold out ≥1 day and ≥1 person.
Never let windows from one session land in two splits. See `02-data-collection.md`
for why. Compute normalization stats after this split, on train sessions only.

## Sanity checks to run every time

- Print the parsed shape and confirm subcarrier count matches expectation (~64 raw).
  A wrong count means the wrong `nexcsi` device string or a corrupt file.
- Plot one amplitude heatmap per class (see `04-ml-visualization.md`) and confirm
  `empty` looks flat/quiet and `walk` shows bursts. If not, stop — the data, not the
  model, is the problem.
- Confirm no NaNs after z-score (a zero-variance subcarrier divides by ~0; use the
  `+1e-8` guard).

## Outputs

Write processed tensors + labels + a split manifest to `data/processed/`:
- `X_train.npy`, `y_train.npy`, and same for val/test
- `norm_stats.npz` (train mean/std) — applied to val/test at load time
- `split_manifest.json` — which session files went to which split (for reproducibility)
