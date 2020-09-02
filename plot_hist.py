""" Easy histograms from MPA data converted to HDF 5 with lst2hdf5"""
import sys
import os

import argparse
from copy import copy

# import numpy as np
import h5py

import matplotlib.pyplot as plt
import matplotlib.colors as mpc

from _common import (
    check_input,
    check_output,
    default_argparser,
)

def hist2d_from_h5hist(h5hist, scaling="log"):
    xchannel = h5hist.attrs["xchannel"]
    ychannel = h5hist.attrs["ychannel"]
    ex = h5hist["EX"][:]
    ey = h5hist["EY"][:]
    hist = h5hist["HIST"][:]

    cmap = copy(plt.cm.plasma)
    cmap.set_under("w", 0)
    cmap.set_over("w", 0)

    fig, ax = plt.subplots()
    if scaling == "log":
        norm = mpc.LogNorm(vmin=1, vmax=hist.max())
    elif scaling == "linear":
        norm = mpc.Normalize(vmin=1, vmax=hist.max())
    if hist.max() > 0:
        img = ax.imshow(
            hist.T,
            norm=norm,
            interpolation=None,
            origin="lower",
            cmap=cmap,
            extent=(ex.min(), ex.max(), ey.min(), ey.max())
        )
        cbar = fig.colorbar(img, ax=ax)
        cbar.set_label("Counts")
    ax.set(
        xlabel=xchannel,
        ylabel=ychannel
    )
    plt.tight_layout()
    return fig

def hist1d_from_h5hist(h5hist, scaling="log"):
    xchannel = h5hist.attrs["xchannel"]
    ex = h5hist["EX"]
    hist = h5hist["HIST"]

    fig, ax = plt.subplots()
    ax.step(ex[:-1], hist, where='post')
    ax.set(
        xlabel=xchannel,
        ylabel="Counts",
        yscale=scaling,
    )
    plt.tight_layout()
    return fig

def _parse_cli_args():
    parser = argparse.ArgumentParser(
        description="Make a histogram from MPA data in HDF5 format.",
        parents=[default_argparser]
    )
    parser.add_argument(
        "--linear",
        help="Scale counts linearly instead of log.",
        action="store_const",
        const="linear",
        default="log"
    )
    parser.add_argument(
        "--pdf",
        help="Save copy of plot as PDF, default if none is given.",
        action="store_true"
    )
    parser.add_argument(
        "--eps",
        help="Save copy of plot as EPS.",
        action="store_true"
    )
    parser.add_argument(
        "--png",
        help="Save copy of plot as PNG.",
        action="store_true"
    )
    parser.add_argument(
        "--pgf",
        help="Save copy of plot as PGF.",
        action="store_true"
    )
    args = parser.parse_args()
    return args

def _main():
    args = _parse_cli_args()
    check_input(args.file)
    save_as = {
        ".pdf":args.pdf,
        ".pgf":args.pgf,
        ".png":args.png,
        ".eps":args.eps,
    }
    if args.out:
        out_name, ext = os.path.splitext(args.out)
        if ext:
            save_as[ext] = True
    else:
        out_name, _ = os.path.splitext(args.file)

    if not any(save_as.values()):
        save_as[".pdf"] = True
    for ext, do_save in save_as.items():
        if do_save:
            check_output(out_name + ext, args.yes)

    with h5py.File(args.file, "r") as f:
        kind = f.attrs["kind"]
        if kind == "1D":
            _fig = hist1d_from_h5hist(f, scaling=args.linear)
        elif kind == "2D":
            _fig = hist2d_from_h5hist(f, scaling=args.linear)

    for ext, do_save in save_as.items():
        if do_save:
            plt.savefig(out_name + ext)


    sys.exit(0)

if __name__ == "__main__":
    _main()
