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

from histograms import Histogram

from fit_synth_spec import make_synth_histogram, fit_overview_plot

def _parse_cli_args():
    parser = argparse.ArgumentParser(
        description="Make a plot for h5fit",
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
        popts = f["Fit"]["p"][:]
        pstds= f["Fit"]["perr"][:]

    histogram = Histogram.from_h5hist(args.file)
    histogram = histogram.cropped_to_adc_cuts()

    synth_histogram = make_synth_histogram(histogram.pcx, histogram, popts, pstds)
    with plt.rc_context(rc={'lines.markersize': 1}):
        _ = fit_overview_plot(histogram, synth_histogram, popts, pstds)

    for ext, do_save in save_as.items():
        if do_save:
            plt.savefig(out_name + ext)


    sys.exit(0)

if __name__ == "__main__":
    _main()
