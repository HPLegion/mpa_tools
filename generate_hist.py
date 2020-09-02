""" Easy histograms from MPA data converted to HDF 5 with lst2hdf5"""
import sys
import os

import argparse

import numpy as np
import h5py

import dask.array as da

from _common import (
    INVALID_ADC_VALUE,
    TYPICAL_DASK_CHUNK,
    DaskProgressBar,
    check_input,
    check_output,
    default_argparser,
)


def dask_hist2d(xdata, ydata, bins, range_=None):
    _x, _y = xdata[:10].compute(), ydata[:10].compute()
    h, ex, ey = np.histogram2d(_x, _y, bins, range_)
    h = np.atleast_3d(h)
    def do_hist2d(x, y):
        hc, _1, _2 = np.histogram2d(x, y, (ex, ey), range_)
        return np.atleast_3d(hc)
    hist = da.map_blocks(do_hist2d, xdata, ydata, chunks=h.shape, dtype=h.dtype)
    hist = hist.sum(axis=-1)
    return hist, ex, ey

def hist2d_from_mpa_data(file_, xchannel, ychannel, nxbins=1024, nybins=1024, chunk_size=TYPICAL_DASK_CHUNK):
    with h5py.File(file_, "r") as f:
        config = f["CFG"]
        xmin = 0
        ymin = 0
        try:
            xmax = config[xchannel].attrs["range"]
        except:
            xmax = INVALID_ADC_VALUE
        try:
            ymax = config[ychannel].attrs["range"]
        except:
            ymax = INVALID_ADC_VALUE
        events = f["EVENTS"]
        xdata = da.from_array(events[xchannel], chunks=chunk_size)
        ydata = da.from_array(events[ychannel], chunks=chunk_size)
        binned, ex, ey = dask_hist2d(xdata, ydata, (nxbins, nybins),
                                     range_=((xmin, xmax), (ymin, ymax)))
        with DaskProgressBar():
            binned = binned.compute()
    return binned, ex, ey

def hist1d_from_mpa_data(file_, xchannel, nxbins=1024, chunk_size=TYPICAL_DASK_CHUNK):
    with h5py.File(file_, "r") as f:
        config = f["CFG"]
        xmin = 0
        try:
            xmax = config[xchannel].attrs["range"]
        except:
            xmax = INVALID_ADC_VALUE - 1
        events = f["EVENTS"]
        xdata = da.from_array(events[xchannel], chunks=chunk_size)
        binned, ex = da.histogram(xdata, nxbins, range=(xmin, xmax))
        with DaskProgressBar():
            binned = binned.compute()
    return binned, ex

def _parse_cli_args():
    parser = argparse.ArgumentParser(
        description="Make a histogram from MPA data in HDF5 format.",
        parents=[default_argparser]
    )
    parser.add_argument(
        "xchannel",
        help="Channel on the x-axis, e.g. ADC0, ADC1, ....",
        type=str,
    )
    parser.add_argument(
        "--nx",
        help="Number of bins on the x-axis.",
        type=int,
        default=1024,
    )
    parser.add_argument(
        "--ychannel",
        help="Channel on the y-axis, forces 2D-histogram.",
        type=str,
        default=""
    )
    parser.add_argument(
        "--ny",
        help="Number of bins on the y-axis.",
        type=int,
        default=1024,
    )
    args = parser.parse_args()
    return args

def _main():
    args = _parse_cli_args()
    check_input(args.file)
    outfile = args.out
    if not outfile:
        outfile = os.path.splitext(args.file)[0] + ".h5hist"
    check_output(outfile, args.yes)

    if not args.ychannel:
        hist, ex = hist1d_from_mpa_data(args.file, args.xchannel, nxbins=args.nx)
        kind = "1D"
    else:
        hist, ex, ey = hist2d_from_mpa_data(args.file, args.xchannel, args.ychannel, nxbins=args.nx, nybins=args.ny)
        kind = "2D"

    with h5py.File(outfile, "w") as f:
        f.attrs["basefile"] = args.file
        f.attrs["kind"] = kind
        f.attrs["xchannel"] = args.xchannel
        f.create_dataset("EX", data=ex)
        f.create_dataset("HIST", data=hist)
        if kind == "2D":
            f.attrs["orientation"] = "x = dim0/rows, y = dim1/cols"
            f.attrs["ychannel"] = args.ychannel
            f.create_dataset("EY", data=ey)


    sys.exit(0)

if __name__ == "__main__":
    _main()
