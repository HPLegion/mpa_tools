""" Easy histograms from MPA data converted to HDF 5 with lst2hdf5"""
import sys
import os

import argparse

import numpy as np
import numba as nb
import h5py

# import dask.array as da
from tqdm.auto import tqdm

from _common import (
    INVALID_ADC_VALUE,
    DaskProgressBar,
    TYPICAL_DASK_CHUNK,
    check_input,
    check_output,
    default_argparser,
)

@nb.njit(cache=True, parallel=True)
def _check_roi_1d(data, dmin, dmax):
    return np.logical_and(np.logical_and(dmin <= data, data <= dmax), data != INVALID_ADC_VALUE)

@nb.njit(cache=True, parallel=True)
def _check_roi_2d_rect(xdata, xmin, xmax, ydata, ymin, ymax):
    return np.logical_and(
        _check_roi_1d(xdata, xmin, xmax),
        _check_roi_1d(ydata, ymin, ymax)
    )


def _make_check_roi_2d_poly(xvert, yvert):
    xvert = xvert.astype(np.float)
    yvert = yvert.astype(np.float)
    _xmin = xvert.min()
    _xmax = xvert.max()
    _ymin = yvert.min()
    _ymax = yvert.max()

    @nb.vectorize([nb.b1(nb.f4, nb.f4)], target="parallel")
    def _check_roi_2d_poly(xpoint, ypoint):
        bbox = _check_roi_2d_rect(xpoint, _xmin, _xmax, ypoint, _ymin, _ymax)
        inside = False
        for i, j in zip(range(xvert.size), range(-1, xvert.size-1)):
            if bbox:
                if (yvert[i] > ypoint) != (yvert[j] > ypoint):
                    if xpoint < (xvert[j]-xvert[i])*(ypoint-yvert[i])/(yvert[j]-yvert[i]) + xvert[i]:
                        inside = not inside
        return inside
    return _check_roi_2d_poly

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
    parser.add_argument(
        "--poly",
        "-p",
        help="2D polygonal ROI: 'X1 Y1 X2 Y2 ...' value of the ROI (inclusive).",
        type=int,
        nargs="+"
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

    kind_of_roi = [args.strip, args.rect, args.poly]
    assert sum(bool(a) for a in kind_of_roi) == 1, "Choose exactly one type of ROI!"

    if args.poly:
        vx = np.array(args.poly[::2])
        vy = np.array(args.poly[1::2])
        _check_roi_2d_poly = _make_check_roi_2d_poly(vx, vy)

    with h5py.File(args.file, "r") as fin, h5py.File(outfile, "w") as fout:
        eve_in = fin["EVENTS"]
        xchan = eve_in[args.xchannel]
        ychan = eve_in[args.ychannel] if args.ychannel else None

        fin.copy("CFG", fout)
        eve_out = fout.create_group("EVENTS")
        roiinf = fout.create_group("ROI")
        for name, vec in eve_in.items():
            stor = eve_out.create_dataset(name, (2,), maxshape=vec.shape, dtype=vec.dtype)

        n = eve_in["TIME"].len()
        chunk_size = TYPICAL_DASK_CHUNK
        stor_pos = 0
        for k in tqdm(range(n//chunk_size+1), desc="Processing"):
            if (k+1)*chunk_size + 1 < n:
                slc = np.s_[k*chunk_size:(k+1)*chunk_size + 1]
            else:
                slc = np.s_[k*chunk_size:]

            xarr = xchan[slc]
            if ychan:
                yarr = ychan[slc]

            if args.strip:
                in_roi = _check_roi_1d(xarr, min(args.strip), max(args.strip))
                kind = "1D"
                roiargs = str(args.strip)

            if args.rect:
                in_roi = _check_roi_2d_rect(
                    xarr, args.rect[0], args.rect[1], yarr, args.rect[2], args.rect[3]
                )
                kind = "2DRect"
                roiargs = str(args.rect)

            if args.poly:
                in_roi = _check_roi_2d_poly(xarr, yarr)
                kind = "2DPoly"
                roiargs = str(args.rect)

            for name, vec in eve_in.items():
                stor = eve_out[name]
                filt = vec[slc][in_roi]
                stor.resize(stor_pos+filt.size, axis=0)
                stor[stor_pos:stor_pos+filt.size] = filt
            stor_pos += filt.size


        roiinf.attrs["kind"] = kind
        roiinf.attrs["roiargs"] = roiargs
        roiinf.attrs["xchannel"] = args.xchannel
        if args.ychannel:
            roiinf.attrs["ychannel"] = args.ychannel


    sys.exit(0)

if __name__ == "__main__":
    _main()