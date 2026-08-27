#!/usr/bin/env python3
"""
four_plot_sequence.py

The four-plot sanity sequence from context/04-ml-visualization.md, generated
from a single nexmon_csi .pcap capture:

    1. Amplitude heatmap (subcarrier x time)   -> is there any structure at all?
    2. Per-subcarrier variance bar chart        -> which subcarriers carry signal?
    3. PCA of the subcarrier dimension over time -> is there a clean event trace?
    4. Spectrogram of PC1                        -> is the energy in the <5 Hz
                                                   human-motion band?

Each panel answers one question before the next. Run it on the Phase 0 pilot
(and later, per class) to decide whether the modality works on this hardware
before committing to deep learning.

Requirements (already in the project .venv):
    numpy, scipy, scikit-learn, matplotlib, nexcsi

Usage:
    python four_plot_sequence.py notebooks/datasets/csi_capture6.pcap
    python four_plot_sequence.py capture.pcap --output plots/four_plot.png --no-hampel
"""

import argparse
import sys

import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import spectrogram
from sklearn.decomposition import PCA

try:
    from nexcsi import decoder
except ImportError:
    sys.exit("Missing dependency 'nexcsi'. Install it with: pip install nexcsi")


def load_csi(pcap_path, device):
    """Read a pcap -> (samples, complex CSI array [n_packets, n_subcarriers])."""
    samples = decoder(device).read_pcap(pcap_path)
    csi = decoder(device).unpack(samples["csi"])
    return samples, csi


def drop_null_pilot(csi):
    """Remove null and pilot subcarriers (they carry no channel information)."""
    md = csi.dtype.metadata or {}
    indices = list(md.get("nulls", [])) + list(md.get("pilots", []))
    kept = np.delete(csi, indices, axis=1)
    print(f"Dropped {len(indices)} null/pilot subcarriers -> {kept.shape[1]} usable.")
    return kept


def packet_timestamps(samples):
    """Elapsed seconds per packet, starting at 0."""
    ts = samples["ts_sec"].astype(np.float64) + samples["ts_usec"].astype(np.float64) * 1e-6
    return ts - ts[0]


def hampel(x, window=7, n_sigma=3.0):
    """
    Per-column Hampel despike. The chip's AGC rescales the whole signal at once,
    creating sharp amplitude jumps that look like motion; a median + MAD filter
    per subcarrier removes them. This is the single most important cleaning step
    on this hardware (see context/03-preprocessing.md).
    """
    x = x.copy()
    k = 1.4826  # MAD -> std for Gaussian data
    half = window // 2
    for c in range(x.shape[1]):
        col = x[:, c]
        padded = np.pad(col, half, mode="edge")
        med = np.empty_like(col)
        mad = np.empty_like(col)
        for i in range(col.size):
            seg = padded[i:i + window]
            m = np.median(seg)
            med[i] = m
            mad[i] = k * np.median(np.abs(seg - m))
        mask = np.abs(col - med) > n_sigma * np.where(mad == 0, 1e-9, mad)
        col[mask] = med[mask]
        x[:, c] = col
    return x


def zscore_per_subcarrier(a):
    mean = a.mean(axis=0, keepdims=True)
    std = a.std(axis=0, keepdims=True)
    std[std == 0] = 1.0
    return (a - mean) / std


def resample_uniform(t, y, fs=10.0):
    """Interpolate an irregularly-sampled series onto a uniform grid at `fs` Hz
    (the project's target CSI rate), so scipy.signal.spectrogram has a
    well-defined sampling frequency. nexmon captures arrive in bursts, so a
    uniform grid is required before any frequency analysis."""
    grid = np.arange(t[0], t[-1], 1.0 / fs)
    return grid, np.interp(grid, t, y), fs


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("pcap", help="path to the captured .pcap file")
    p.add_argument("--device", default="raspberrypi",
                   choices=["raspberrypi", "nexus5", "nexus6p", "rtac86u"],
                   help="chip/device used for capture (default: raspberrypi)")
    p.add_argument("--output", default=None,
                   help="output image path (default: <pcap>_four_plot.png)")
    p.add_argument("--no-hampel", action="store_true",
                   help="skip the Hampel despike step")
    p.add_argument("--show", action="store_true", help="show the figure interactively")
    args = p.parse_args()

    out = args.output or (args.pcap.rsplit(".", 1)[0] + "_four_plot.png")

    print(f"Reading {args.pcap} (device={args.device}) ...")
    samples, csi = load_csi(args.pcap, args.device)
    print(f"Loaded {csi.shape[0]} packets x {csi.shape[1]} subcarriers.")

    t = packet_timestamps(samples)
    duration = t[-1] if t[-1] > 0 else 1.0
    rate = csi.shape[0] / duration
    print(f"Capture duration: {duration:.1f} s  (~{rate:.1f} packets/s average)")

    csi = drop_null_pilot(csi)
    amp = np.abs(csi)
    if not args.no_hampel:
        print("Hampel despike ...")
        amp = hampel(amp)
    amp_z = zscore_per_subcarrier(amp)

    # ---- panel 3 data: PCA over the subcarrier dimension --------------------
    pcs = PCA(n_components=3).fit_transform(amp_z)  # (n_packets, 3)

    # ---- panel 4 data: spectrogram of PC1 ---------------------------------
    grid, pc1_u, fs = resample_uniform(t, pcs[:, 0])
    nperseg = int(min(256, max(32, pc1_u.size // 8)))
    f, tau, Sxx = spectrogram(pc1_u, fs=fs, nperseg=nperseg,
                              noverlap=nperseg // 2, scaling="density")

    # ---- figure ----------------------------------------------------------
    fig, axes = plt.subplots(2, 2, figsize=(15, 9))
    fig.suptitle(f"CSI four-plot sanity sequence -- {args.pcap.split('/')[-1]}",
                 fontsize=15)

    # 1. amplitude heatmap
    ax = axes[0, 0]
    vmax = np.percentile(np.abs(amp_z), 98)
    mesh = ax.pcolormesh(t, np.arange(amp_z.shape[1]), amp_z.T,
                         shading="auto", cmap="RdBu_r", vmin=-vmax, vmax=vmax)
    ax.set_title("1. Amplitude heatmap  --  is there any structure?")
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Usable subcarrier index")
    fig.colorbar(mesh, ax=ax, label="amplitude (z-scored / subcarrier)")

    # 2. per-subcarrier relative fluctuation
    #    Raw variance is dominated by frequency-selective fading (some
    #    subcarriers sit ~30x higher than others), so normalise each by its own
    #    mean first: what is left is how much that subcarrier *moves* over time.
    ax = axes[0, 1]
    rel = amp.std(axis=0) / (amp.mean(axis=0) + 1e-9)
    ax.bar(np.arange(rel.size), rel, color="#3b7dd8")
    ax.set_title("2. Per-subcarrier fluctuation  --  which subcarriers carry signal?")
    ax.set_xlabel("Usable subcarrier index")
    ax.set_ylabel("std / mean of amplitude")

    # 3. PCA over time (plotted vs packet index -- captures arrive in bursts, so
    #    a wall-clock x-axis would draw long straight lines across idle gaps)
    ax = axes[1, 0]
    n = np.arange(pcs.shape[0])
    for i, c in enumerate(["#d1495b", "#2e933c", "#3b7dd8"]):
        ax.plot(n, pcs[:, i], color=c, linewidth=0.7, label=f"PC{i + 1}")
    ax.set_title("3. PCA of subcarriers over time  --  is there a clean event trace?")
    ax.set_xlabel("Packet index")
    ax.set_ylabel("component value")
    ax.legend(loc="upper right", fontsize=8)

    # 4. spectrogram of PC1
    ax = axes[1, 1]
    band = f <= 5.0
    mesh = ax.pcolormesh(tau, f[band], 10 * np.log10(Sxx[band] + 1e-12),
                         shading="auto", cmap="magma")
    ax.set_title("4. Spectrogram of PC1  --  is the energy under ~5 Hz?")
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Frequency (Hz)")
    fig.colorbar(mesh, ax=ax, label="power (dB)")

    fig.tight_layout(rect=[0, 0, 1, 0.96])
    fig.savefig(out, dpi=150)
    print(f"Saved {out}")
    if args.show:
        plt.show()


if __name__ == "__main__":
    main()
