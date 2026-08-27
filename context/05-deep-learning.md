# 05 — Deep Learning Models

**What this covers / why it matters:** The progression of models from a
zero-training baseline to the headline Mamba + self-supervised system. Each stage
earns the next — you never reach for the big model until the small one has given you
a number to beat. Model choice follows the task (classification here), not the other
way around.

## The progression (build in this order)

1. **Threshold baseline (no training).** Rolling variance / z-score on PC1 (see
   `04`). Establishes that classes are separable at all and gives the naive number
   every learned model must beat. Costs nothing; goes in the paper.

2. **Classical ML baseline.** Per-window hand features (per-subcarrier variance,
   low-band spectral energy, top PCA components) → RandomForest or SVM. Fast, strong,
   honest. Often competitive with tiny data — a fair bar for the deep models.

3. **CNN baseline.** A small 1D/2D CNN over the window tensor `(T, C)`. The
   "standard deep learning" reference. Keep it lightweight (precedent: a
   ~0.1–0.3 M-param CNN reached strong WiFi results on a Colab T4 — small models are
   legitimate here). This is the convolutional model in the plan; treat the window as
   a (time × subcarrier) image, Conv → BN → ReLU stacks → global pool → linear head.

4. **Mamba (main model).** A Mamba sequence model over the window (time as the
   sequence axis, subcarriers as features). *Why Mamba:* linear-time sequence modeling
   for long CSI streams, cheaper than attention at our sequence lengths. Be honest in
   the paper about why Mamba over a ViT/LSTM — link it to WiMamba precedent.

5. **Mamba + self-supervised pretraining (headline).** Pretrain the Mamba backbone
   on **unlabeled ambient CSI** with a masked-reconstruction objective, then
   fine-tune a small classification head on the labeled sessions.

## Self-supervised pretraining — the core research bet

**Why:** labeled CSI is expensive; unlabeled ambient CSI is cheap. If pretraining on
the cheap data lets us fine-tune on little labeled data and still win, that's the
contribution. Precedent: WiFi-JEPA (masked-latent prediction beats from-scratch and
beats vision-style SSL), WiMamba (Mamba backbone pretrained on unlabeled CSI).

**Objective (masked reconstruction), shape of it:**
```python
# mask spans of the CSI window (time spans, subcarrier bands, or both),
# train the model to reconstruct the masked positions from the visible ones.
# loss = MSE on masked positions only.
```
Masking along **time** forces learning the channel's temporal structure; masking
**subcarriers** forces cross-frequency structure. Which helps most is an ablation
(below). Masked-latent-prediction (JEPA-style, predict in latent space rather than
raw CSI) is the more robust variant since it ignores hardware artifacts in raw CSI —
consider it if raw-reconstruction pretraining underperforms.

**Sizing caution:** CSI datasets are tiny vs. vision/text corpora; SSL can overfit on
a few thousand sequences. Start small (few Mamba blocks, modest hidden size). Validate
that pretraining actually helped with a linear probe: a linear classifier on frozen
pretrained features should beat one on random-init features. If it doesn't, train
supervised-only for now and revisit once more ambient hours are collected.

## The experiments that make it a paper

Mirror how the reference papers structure evidence:

1. **Main results table** — all five models, accuracy/F1 on the session-disjoint test
   set (empty/still/walk; optionally multi-person).
2. **SSL ablation (core contribution)** — Mamba from-scratch vs. pretrained.
3. **Label-efficiency curve** — accuracy vs. labeled-data fraction (10/25/50/100%),
   scratch vs. pretrained. If pretraining helps most when labels are scarce, that's
   the money figure (WiFi-JEPA Table 5 logic).
4. **Masking-strategy ablation** — time vs. subcarrier vs. random masking.
5. **Cross-condition generalization** — held-out day / held-out person; report the
   drop honestly (both RePos and WiFi-JEPA foreground this as a strength).

## Training practicalities

- Compute: parsing/visualization/classical ML run on CPU. Use the Colab T4 only for
  CNN/Mamba training and SSL pretraining. Don't burn GPU hours on data wrangling.
- Optimizer: AdamW, cosine schedule, early stopping on a session-disjoint val split.
- Augmentation: light temporal jitter and Gaussian noise on amplitude (used by the
  reference papers) — but never augmentations that break channel structure.
- Metrics: accuracy + macro-F1 (classes may be imbalanced); confusion matrix per
  model; for presence, also precision/recall (a missed person matters more than a
  false alarm, depending on the application).

## Architecture-follows-task (future phases)

If the project later moves to pose (camera-labeled), the decoder changes to a
PETR/GCN-style head like the reference papers — not the classification head here. Let
each phase's task dictate architecture rather than fixing it up front. Keep such
extensions under an explicit future-work heading (see `06-execution-plan.md`).
