#!/usr/bin/env python3
"""
csi_spectrogram.py

Generate CSI amplitude (and optionally phase) spectrograms from a
nexmon_csi .pcap capture — a heatmap of amplitude over time (x-axis)
and subcarrier index (y-axis).

For captures with many packets, the output is split into multiple
images (chunks) so each packet gets real pixel width instead of being
squished into one oversized plot.

Requirements:
    pip install nexcsi numpy matplotlib

Usage:
    python csi_spectrogram.py capture.pcap
    python csi_spectrogram.py capture.pcap --packets-per-image 300
    python csi_spectrogram.py capture.pcap --theme light --include-phase
    python csi_spectrogram.py capture.pcap --show

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
    much smaller time-varying changes caused by motion. Normalizing each
    subcarrier to its own mean/std puts every column on equal footing so
    changes *over time* carry the contrast instead.
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


def style_dark(fig, ax):
    fig.patch.set_facecolor("black")
    ax.set_facecolor("black")
    ax.tick_params(colors="white")
    ax.xaxis.label.set_color("white")
    ax.yaxis.label.set_color("white")
    ax.title.set_color("white")
    for spine in ax.spines.values():
        spine.set_color("white")


def plot_heatmap(ax, t, values, ylabel, cbar_label, cmap, title, vmin, vmax, theme):
    n_subcarriers = values.shape[1]
    sc_idx = np.arange(n_subcarriers)
    mesh = ax.pcolormesh(t, sc_idx, values.T, shading="auto", cmap=cmap, vmin=vmin, vmax=vmax)
    ax.set_xlabel("Time (s)")
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    fig = ax.get_figure()
    cbar = fig.colorbar(mesh, ax=ax, label=cbar_label)
    if theme == "dark":
        style_dark(fig, ax)
        cbar.ax.yaxis.label.set_color("white")
        cbar.ax.tick_params(colors="white")
        cbar.outline.set_edgecolor("white")


def main():
    parser = argparse.ArgumentParser(
        description="Generate CSI spectrogram(s) (amplitude heatmap) from a nexmon_csi pcap file."
    )
    parser.add_argument("pcap", help="Path to the captured .pcap file")
    parser.add_argument("--device", default="raspberrypi",
                         choices=["raspberrypi", "nexus5", "nexus6p", "rtac86u"],
                         help="Chip/device used for capture (default: raspberrypi)")
    parser.add_argument("--output-prefix", default=None,
                         help="Output filename prefix (default: <pcap-name>_spectrogram)")
    parser.add_argument("--strip", default="zero", choices=["zero", "drop", "keep"],
                         help="How to handle null/pilot subcarriers (default: zero)")
    parser.add_argument("--linear", action="store_true",
                         help="Plot linear amplitude instead of dB scale")
    parser.add_argument("--include-phase", action="store_true",
                         help="Also plot a sanitized (unwrapped) phase panel below amplitude")
    parser.add_argument("--no-normalize", action="store_true",
                         help="Skip per-subcarrier z-score normalization (raw amplitude/dB, "
                              "usually looks washed out due to subcarrier-to-subcarrier gain differences)")
    parser.add_argument("--theme", default="dark", choices=["dark", "light"],
                         help="'dark' = black background + hot colormap (default), 'light' = white background")
    parser.add_argument("--cmap", default=None,
                         help="Matplotlib colormap override. Default: 'inferno' (dark theme) or "
                              "'RdBu_r'/'viridis' (light theme)")
    parser.add_argument("--clip-percentile", type=float, default=2.0,
                         help="Clip color scale to [p, 100-p] percentiles instead of raw min/max (default: 2.0)")
    parser.add_argument("--packets-per-image", type=int, default=500,
                         help="Max packets per output image before splitting into multiple images (default: 500)")
    parser.add_argument("--pixels-per-packet", type=float, default=6.0,
                         help="Horizontal pixels dedicated to each packet, controls image width (default: 6.0)")
    parser.add_argument("--dpi", type=int, default=150, help="Output image DPI (default: 150)")
    parser.add_argument("--show", action="store_true", help="Display each plot interactively")
    args = parser.parse_args()

    output_prefix = args.output_prefix or (args.pcap.rsplit(".", 1)[0] + "_spectrogram")

    print(f"Reading {args.pcap} (device={args.device}) ...")
    samples, csi = load_csi(args.pcap, args.device)
    n_packets, n_subcarriers = csi.shape
    print(f"Loaded {n_packets} packets x {n_subcarriers} subcarriers.")

    t = packet_timestamps(samples)
    if t[-1] > 0:
        print(f"Capture duration: {t[-1]:.2f} s  (~{n_packets / t[-1]:.1f} packets/sec average)")

    csi = strip_null_pilot(csi, args.strip)
    amplitude = compute_amplitude(csi, db=not args.linear)
    phase = compute_phase(csi, unwrap=True) if args.include_phase else None

    normalize = not args.no_normalize
    amp_label = "Amplitude (dB)" if not args.linear else "Amplitude (linear)"

    if args.theme == "dark":
        # Dark theme: brightness = magnitude of change against a black background,
        # matching a classic hot-colormap spectrogram look.
        cmap = args.cmap or "inferno"
        if normalize:
            amplitude = np.abs(normalize_per_subcarrier(amplitude))
            amp_label += ", |z-score| per subcarrier"
        vmin = 0.0
        _, vmax = percentile_limits(amplitude, args.clip_percentile, 100 - args.clip_percentile)
    else:
        if normalize:
            amplitude = normalize_per_subcarrier(amplitude)
            amp_label += ", z-scored per subcarrier"
            cmap = args.cmap or "RdBu_r"
            vmin, vmax = percentile_limits(amplitude, args.clip_percentile, 100 - args.clip_percentile)
            vmax = max(abs(vmin), abs(vmax))
            vmin = -vmax
        else:
            cmap = args.cmap or "viridis"
            vmin, vmax = percentile_limits(amplitude, args.clip_percentile, 100 - args.clip_percentile)

    if phase is not None:
        phase_vmin, phase_vmax = percentile_limits(phase, args.clip_percentile, 100 - args.clip_percentile)
        phase_cmap = "magma" if args.theme == "dark" else cmap

    # --- split into chunks so packets aren't squished into one oversized image ---
    chunk_size = max(1, args.packets_per_image)
    n_chunks = int(np.ceil(n_packets / chunk_size))
    print(f"Writing {n_chunks} image(s), up to {chunk_size} packets each ...")

    for i in range(n_chunks):
        start, end = i * chunk_size, min((i + 1) * chunk_size, n_packets)
        width_in = max(6.0, (end - start) * args.pixels_per_packet / args.dpi)

        n_panels = 2 if phase is not None else 1
        fig, axes = plt.subplots(n_panels, 1, figsize=(width_in, 5 * n_panels), sharex=True)
        axes = np.atleast_1d(axes)

        suffix = "" if n_chunks == 1 else f"_part{i + 1:03d}"
        title_suffix = "" if n_chunks == 1 else f" (packets {start}-{end})"

        plot_heatmap(axes[0], t[start:end], amplitude[start:end], "Subcarrier index", amp_label, cmap,
                     f"CSI Amplitude Spectrogram — {args.pcap.split('/')[-1]}{title_suffix}",
                     vmin, vmax, args.theme)

        if phase is not None:
            plot_heatmap(axes[1], t[start:end], phase[start:end], "Subcarrier index",
                         "Phase (rad, unwrapped)", phase_cmap, "CSI Phase",
                         phase_vmin, phase_vmax, args.theme)

        fig.tight_layout()
        output_path = f"{output_prefix}{suffix}.png"
        fig.savefig(output_path, dpi=args.dpi,
                    facecolor=fig.get_facecolor() if args.theme == "dark" else "white")
        print(f"  Saved {output_path}  ({end - start} packets, {width_in:.1f} in wide)")

        if args.show:
            plt.show()
        plt.close(fig)


if __name__ == "__main__":
    main()
