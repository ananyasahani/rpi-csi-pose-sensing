# 04 — Visualization & Unsupervised Inference

**What this covers / why it matters:** How to *see* whether there's real,
separable signal in the CSI before committing to deep learning, and how to extract
early inferences with no labels. Every one of these is a figure or sanity gate, not
a final result — they tell you whether to proceed and they become supporting
evidence in the paper.

## The four-plot sanity sequence (run in this order)

Run these first, on the Week 0 pilot, per class. Each answers one question before
the next.

1. **Amplitude heatmap** (subcarrier × time). *Is there any structure at all?*
   `empty` should be flat/quiet; `walk` should show bright bursts of variance.

2. **Per-subcarrier variance bar chart.** *Which subcarriers carry signal?* Flat-zero
   bars are dead/pilot leftovers to confirm-drop; high-variance ones are where motion
   lives.

3. **PCA of the subcarrier dimension over time.** *Is there a clean event trace?*
   Reduce ~52 subcarriers to 2–3 components and plot over time. Motion should show as
   clear spikes in PC1/PC2; `empty` should be flat. PCA extracts the dominant
   motion-driven variance and suppresses noise.

4. **Spectrogram of PC1.** *Is the energy in the human-motion band?* Real motion sits
   under ~5 Hz (walking/gestures), breathing under ~0.5 Hz. Broadband energy or
   instantaneous full-spectrum stripes = noise/AGC, not a person.

## Telling "person" from "noise" (the discriminators)

- **Temporal correlation.** A body persists across consecutive packets; noise
  decorrelates instantly. Autocorrelation of a moving segment decays slowly; noise
  drops to ~0 after 1–2 lags.
- **Frequency-selectivity.** An AGC gain-step multiplies all subcarriers at once →
  uniform jump across the cross-subcarrier correlation matrix. Real motion is
  frequency-selective → patchy, shifting correlation. Big uniform block = artifact;
  textured/partial = real.
- **Low-frequency concentration.** Human motion energy is <~5 Hz on the spectrogram.
  Flat broadband energy with sharp vertical stripes = noise.

## What to expect with Tx/Rx in the same room

- Direct path dominates → a body's reflection is a **small perturbation on a large
  stable baseline**. Don't expect huge relative swings; expect subtle textured
  disturbance on a steady baseline.
- Sensitivity depends on **where** the person is relative to the Tx–Rx line (Fresnel
  zones), not just whether they're "in the room." Weak signal? Have someone cross the
  direct line before concluding the rig doesn't work.
- The `empty` baseline is NOT flat amplitude — static furniture creates a fixed
  multipath fingerprint. You're looking for *deviation from that fixed pattern over
  time*, not deviation from zero.

## UMAP for cluster inspection (use, but read this caveat)

UMAP on windowed features (variance, low-band spectral energy, top PCs, or a model's
embeddings) is excellent for *seeing* whether classes separate — better than PCA for
visualization.

**Caveat, stated plainly:** UMAP is a *visualization/hypothesis* tool, not a
classifier. Its distances and cluster sizes are NOT quantitatively meaningful. Do not
claim "2 vs 3 people are separable" *because* UMAP shows blobs. Use UMAP to form the
hypothesis, then prove it with a trained classifier and held-out accuracy. This is
exactly how the reference papers use PCA/feature plots — supporting evidence, not the
result.

```python
import umap
emb = umap.UMAP(n_neighbors=15, min_dist=0.1).fit_transform(features)  # (N, 2)
# scatter, colored by label → eyeball class structure
```

## Unsupervised inference (no labels needed)

Useful on ambient captures and as early results:

- **PCA + variance thresholding** — the simplest detector: flag windows whose PC
  variance exceeds a baseline multiple as "something happened." Zero training.
- **Rolling z-score on PC1** — immediate lightweight presence detector; spikes above
  ~3σ are candidate events. Good first pass on unlabeled ambient data.
- **Change-point detection** — `ruptures` (PELT / BOCPD) on a rolling feature
  segments a long ambient stream into stable vs. transitioning regions. Natural fit
  for one long recording rather than pre-cut samples.
- **Clustering (k-means / GMM)** on windowed features — do clusters roughly split into
  quiet vs. active? Validates structure before deep learning (precedent: unsupervised
  occupancy via self-organizing maps).
- **Autoencoder anomaly detection** — train a small AE to reconstruct mostly-ambient
  windows; high reconstruction error flags candidate presence. Same idea as the
  masked-reconstruction pretraining in `05`, used directly as a detector.

## How these feed the paper

- Four-plot sequence → a "signal characterization" figure proving the modality works
  on this hardware.
- UMAP → a "class structure" figure motivating the classifier.
- Unsupervised detectors → a labelfree baseline the trained models must beat.
