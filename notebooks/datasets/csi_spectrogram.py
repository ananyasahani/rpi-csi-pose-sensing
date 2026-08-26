#!/usr/bin/env python3
"""
csi_spectrogram.py

Generate a CSI amplitude (and optionally phase) spectrogram from a
nexmon_csi .pcap capture — a heatmap of amplitude over time (x-axis)
and subcarrier index (y-axis).

Requirements:
    pip install nexcsi numpy matplotlib

Usage:
    python csi_spectrogram.py capture.pcap
    python csi_spectrogram.py capture.pcap --device raspberrypi --output out.png
    python csi_spectrogram.py capture.pcap --strip drop --include-phase --show

Device options (must match the chip that captured the data):
    raspberrypi, nexus5, nexus6p, rtac86u
"""

import argparse
import sys

import numpy as np
import matplotlib.pyplot as plt

try:
    from nexcsi import decoder
except ImportError:
    sys.exit("Missing dependency. Install it with: pip install nexcsi")


def load_csi(pcap_path, device):
    """Read a pcap and return (samples, complex CSI array [n_packets, n_subcarriers])."""
    samples = decoder(device).read_pcap(pcap_path)
    csi = decoder(device).unpack(samples["csi"])
    return samples, csi


def strip_null_pilot(csi, mode):
    """Zero out or drop null/pilot subcarriers. mode: 'zero' | 'drop' | 'keep'."""
    if mode == "keep":
        return csi

    nulls = list(csi.dtype.metadata.get("nulls", []))
    pilots = list(csi.dtype.metadata.get("pilots", []))
    indices = nulls + pilots

    if mode == "zero":
        csi = csi.copy()
        csi[:, indices] = 0
        print(f"Zeroed {len(nulls)} null and {len(pilots)} pilot subcarriers.")
    elif mode == "drop":
        csi = np.delete(csi, indices, axis=1)
        print(f"Dropped {len(nulls)} null and {len(pilots)} pilot subcarriers "
              f"-> {csi.shape[1]} subcarriers remaining.")
    return csi


def packet_timestamps(samples):
    """Return elapsed time in seconds for each packet, starting at 0."""
    ts = samples["ts_sec"].astype(np.float64) + samples["ts_usec"].astype(np.float64) * 1e-6
    return ts - ts[0]


def compute_amplitude(csi, db=True):
    amplitude = np.abs(csi)
    if db:
        amplitude = 20 * np.log10(amplitude + 1e-6)  # avoid log(0)
    return amplitude


def normalize_per_subcarrier(values):
    """
    Z-score each subcarrier (column) independently.

    Raw CSI amplitude varies enormously from one subcarrier to the next
    (frequency-selective fading, antenna gain, etc.) — that static
    variation dominates a single global color scale and drowns out the
    much smaller time-varying changes caused by motion, which is what
    makes an un-normalized heatmap look washed out. Normalizing each
    subcarrier to its own mean/std puts every column on equal footing so
    the *changes over time* — the part you actually care about — carry
    the contrast.
    """
    mean = values.mean(axis=0, keepdims=True)
    std = values.std(axis=0, keepdims=True)
    std[std == 0] = 1  # guard against divide-by-zero on dead subcarriers
    return (values - mean) / std


def percentile_limits(values, low=2, high=98):
    """Robust color limits — ignores extreme outliers instead of using raw min/max."""
    return np.percentile(values, low), np.percentile(values, high)


def compute_phase(csi, unwrap=True):
    phase = np.angle(csi)
    if unwrap:
        phase = np.unwrap(phase, axis=0)  # unwrap across time per subcarrier
    return phase


def plot_heatmap(ax, t, values, ylabel, cbar_label, cmap, title, vmin=None, vmax=None):
    n_subcarriers = values.shape[1]
    sc_idx = np.arange(n_subcarriers)
    mesh = ax.pcolormesh(t, sc_idx, values.T, shading="auto", cmap=cmap, vmin=vmin, vmax=vmax)
    ax.set_xlabel("Time (s)")
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    fig = ax.get_figure()
    fig.colorbar(mesh, ax=ax, label=cbar_label)


def main():
    parser = argparse.ArgumentParser(
        description="Generate a CSI spectrogram (amplitude heatmap) from a nexmon_csi pcap file."
    )
    parser.add_argument("pcap", help="Path to the captured .pcap file")
    parser.add_argument("--device", default="raspberrypi",
                         choices=["raspberrypi", "nexus5", "nexus6p", "rtac86u"],
                         help="Chip/device used for capture (default: raspberrypi)")
    parser.add_argument("--output", default=None,
                         help="Output image path (default: <pcap-name>_spectrogram.png)")
    parser.add_argument("--strip", default="zero", choices=["zero", "drop", "keep"],
                         help="How to handle null/pilot subcarriers (default: zero)")
    parser.add_argument("--linear", action="store_true",
                         help="Plot linear amplitude instead of dB scale")
    parser.add_argument("--include-phase", action="store_true",
                         help="Also plot a sanitized (unwrapped) phase panel below amplitude")
    parser.add_argument("--no-normalize", action="store_true",
                         help="Skip per-subcarrier z-score normalization (use raw amplitude/dB scale, "
                              "which usually looks washed out due to subcarrier-to-subcarrier gain differences)")
    parser.add_argument("--cmap", default=None,
                         help="Matplotlib colormap. Default: 'RdBu_r' when normalized, 'viridis' otherwise")
    parser.add_argument("--clip-percentile", type=float, default=2.0,
                         help="Clip color scale to [p, 100-p] percentiles instead of raw min/max (default: 2.0)")
    parser.add_argument("--show", action="store_true", help="Display the plot interactively")
    args = parser.parse_args()

    output_path = args.output or (args.pcap.rsplit(".", 1)[0] + "_spectrogram.png")

    print(f"Reading {args.pcap} (device={args.device}) ...")
    samples, csi = load_csi(args.pcap, args.device)
    n_packets, n_subcarriers = csi.shape
    print(f"Loaded {n_packets} packets x {n_subcarriers} subcarriers.")

    t = packet_timestamps(samples)
    if t[-1] > 0:
        print(f"Capture duration: {t[-1]:.2f} s  (~{n_packets / t[-1]:.1f} packets/sec average)")

    csi = strip_null_pilot(csi, args.strip)
    amplitude = compute_amplitude(csi, db=not args.linear)

    normalize = not args.no_normalize
    amp_label = "Amplitude (dB)" if not args.linear else "Amplitude (linear)"
    if normalize:
        amplitude = normalize_per_subcarrier(amplitude)
        amp_label += ", z-scored per subcarrier"
        cmap = args.cmap or "RdBu_r"
        vmin, vmax = percentile_limits(amplitude, args.clip_percentile, 100 - args.clip_percentile)
        # center the diverging colormap on zero so "no change" reads as neutral
        vmax = max(abs(vmin), abs(vmax))
        vmin = -vmax
    else:
        cmap = args.cmap or "viridis"
        vmin, vmax = percentile_limits(amplitude, args.clip_percentile, 100 - args.clip_percentile)

    n_panels = 2 if args.include_phase else 1
    fig, axes = plt.subplots(n_panels, 1, figsize=(12, 5 * n_panels), sharex=True)
    axes = np.atleast_1d(axes)

    plot_heatmap(axes[0], t, amplitude, "Subcarrier index", amp_label, cmap,
                 f"CSI Amplitude Spectrogram — {args.pcap.split('/')[-1]}", vmin=vmin, vmax=vmax)

    if args.include_phase:
        phase = compute_phase(csi, unwrap=True)
        phase_vmin, phase_vmax = percentile_limits(phase, args.clip_percentile, 100 - args.clip_percentile)
        plot_heatmap(axes[1], t, phase, "Subcarrier index", "Phase (rad, unwrapped)",
                     cmap, "CSI Phase", vmin=phase_vmin, vmax=phase_vmax)

    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    print(f"Saved spectrogram to {output_path}")

    if args.show:
        plt.show()


if __name__ == "__main__":
    main()
