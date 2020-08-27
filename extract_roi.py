""" Easy histograms from MPA data converted to HDF 5 with lst2hdf5"""
import sys
import os

import argparse

import numpy as np
import numba as nb
import h5py

import dask.array as da
from tqdm.auto import tqdm

from _common import (
    INVALID_ADC_VALUE,
    DaskProgressBar,
    TYPICAL_DASK_CHUNK,
    check_input,
    check_output,
    default_argparser,
)

@nb.njit(cache=True)
def _check_roi_1d(data, dmin, dmax):
    return np.logical_and(np.logical_and(dmin <= data, data <= dmax), data != INVALID_ADC_VALUE)

@nb.njit(cache=True)
def _check_roi_2d_rect(xdata, xmin, xmax, ydata, ymin, ymax):
    return np.logical_and(
        _check_roi_1d(xdata, xmin, xmax),
        _check_roi_1d(ydata, ymin, ymax)
    )

def _get_boolean_array(check, *args):
    res = da.map_blocks(check, *args)
    return res

def _parse_cli_args():
    parser = argparse.ArgumentParser(
        description="Define a ROI and write the IDs of the included events into the HDF file."\
                    "\nSpecify only one type of ROI at a time",
        parents=[default_argparser]
    )
    parser.add_argument(
        "xchannel",
        help="Channel for 1D ROI / X-channel for 2D ROI, e.g. ADC0, ADC1, ....",
        type=str,
    )
    parser.add_argument(
        "--ychannel",
        help="Y-channel for 2D ROI",
        type=str,
        default=""
    )
    parser.add_argument(
        "--strip",
        "-s",
        help="1D ROI: 'Min Max' value of the ROI (inclusive).",
        type=int,
        nargs=2
    )
    parser.add_argument(
        "--rect",
        "-r",
        help="2D rectangular ROI: 'Xmin Xmax Ymin Ymax' value of the ROI (inclusive).",
        type=int,
        nargs=4
    )

    args = parser.parse_args()
    return args

def _main():
    args = _parse_cli_args()
    check_input(args.file)
    outfile = args.out
    if not outfile:
        outfile = os.path.splitext(args.file)[0] + ".h5roi"
    check_output(outfile, args.yes)

    kind_of_roi = [args.strip, args.rect]
    assert sum(bool(a) for a in kind_of_roi) == 1, "Choose exactly one type of ROI!"

    with h5py.File(args.file, "r") as fin, h5py.File(outfile, "w") as fout:
        # events = fin["EVENTS"]
        # n = events["TIME"].len()
        # for k in tqdm(range(n//chunk_size+1), desc="Processing"):
        #     if (k+1)*chunk_size + 1 < n:
        #         a = events[xchannel][k*chunk_size:(k+1)*chunk_size + 1]
        #         b = events[ychannel][k*chunk_size:(k+1)*chunk_size + 1]
        #     else:
        #         a = events[xchannel][k*chunk_size:]
        #         b = events[ychannel][k*chunk_size:]


        # fin.copy("CFG", fout)
        xarr = da.from_array(fin["EVENTS"][args.xchannel], chunks=TYPICAL_DASK_CHUNK)
        if args.strip:
            ids = _get_boolean_array(_check_roi_1d, xarr, min(args.strip), max(args.strip))
            kind = "1D"
            roiargs = str(args.strip)

        if args.rect:
            yarr = da.from_array(fin["EVENTS"][args.ychannel], chunks=TYPICAL_DASK_CHUNK)
            ids = _get_boolean_array(
                _check_roi_2d_rect,
                xarr, args.rect[0], args.rect[1], yarr, args.rect[2], args.rect[3]
            )
            kind = "2DRect"
            roiargs = str(args.rect)

        # eve_out = fout.create_group("EVENTS")
        out = fout.create_dataset("ROI", shape=fin["EVENTS"][args.xchannel].shape, dtype="?")
        with DaskProgressBar():
            # for ds in fin["EVENTS"].values():
            #     ds = da.from_array(ds)
            #     out = eve_out.create_dataset(ds.name, shape=(1000,), maxshape=ds.shape, dtype=ds.dtype)
            #     dat = ds[ids]
            #     dat.compute_chunk_sizes()
            da.store(ids, out)
        fout.attrs["kind"] = kind
        fout.attrs["roiargs"] = roiargs
        fout.attrs["xchannel"] = args.xchannel
        if args.ychannel:
            fout.attrs["ychannel"] = args.ychannel


    sys.exit(0)

if __name__ == "__main__":
    _main()