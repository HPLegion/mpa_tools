""" Easy histograms from MPA data converted to HDF 5 with lst2hdf5"""
import sys
import os
from shutil import copyfile

import argparse
from copy import copy

import numpy as np
import h5py

import matplotlib.pyplot as plt
import matplotlib.colors as mpc

from _common import (
    check_input,
    check_output,
    default_argparser,
)

from histograms import Histogram

from fit_synth_spec import bisection_fit

def _parse_cli_args():
    parser = argparse.ArgumentParser(
        description="Fit a time resolved spectrum in h5hist format.",
        parents=[default_argparser]
    )
    args = parser.parse_args()
    return args

def _main():
    args = _parse_cli_args()
    check_input(args.file)
    outfile = args.out
    if not outfile:
        outfile = os.path.splitext(args.file)[0] + ".h5fit"
    check_output(outfile, args.yes)

    histogram = Histogram.from_h5hist(args.file)
    histogram = histogram.cropped_to_adc_cuts()

    popts, pstds = bisection_fit(histogram.pcx, histogram.counts, n=2)

    copyfile(args.file, outfile)
    with h5py.File(outfile, "a") as f:
        fit = f.require_group("Fit")
        f.attrs["basefile"] = os.path.basename(args.file)
        fit.create_dataset("p", data=popts)
        fit.create_dataset("perr", data=pstds)


    sys.exit(0)

if __name__ == "__main__":
    _main()
