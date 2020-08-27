""" Easy histograms from MPA data converted to HDF 5 with lst2hdf5"""
import sys
import os

import argparse
from copy import copy

import numpy as np
# import numba as nb
import h5py

import matplotlib.pyplot as plt
import matplotlib.colors as mpc

import dask.array as da

from _common import INVALID_ADC_VALUE, DaskProgressBar
# INVALID_INDEX = -1


# @nb.njit(cache=True, parallel=True)
# def index_data(data, dmin, dmax, nbins):
#     m = (nbins-1)/(dmax - dmin)
#     b = -m*dmin
#     idx = np.zeros_like(data, dtype=np.int32)
#     idx[:] = m * data + b
#     idx = np.minimum(idx, nbins-1)
#     idx = np.maximum(idx, 0)
#     idx[data==INVALID_ADC_VALUE] = INVALID_INDEX
#     edges = (np.arange(nbins)-b)/m
#     return edges, idx

# @nb.njit(cache=True, parallel=True)
# def hist1d(data, dmin, dmax, nbins):
#     edges, idx = index_data(data, dmin, dmax, nbins)
#     binned = np.zeros(nbins, dtype=np.int32)
#     for i in idx:
#         if i != INVALID_INDEX:
#             binned[i] += 1
#     return edges, binned

# @nb.njit(cache=True, parallel=True)
# def hist2d(datax, dxmin, dxmax, nxbins, datay, dymin, dymax, nybins):
#     ex, ix = index_data(datax, dxmin, dxmax, nxbins)
#     ey, iy = index_data(datay, dymin, dymax, nybins)
#     binned = np.zeros((nybins, nxbins), dtype=np.int32)
#     for x, y in zip(ix, iy):
#         if x != INVALID_INDEX and y != INVALID_INDEX:
#             binned[y, x] += 1
#     return ex, ey, binned

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

def hist2d_from_mpa_data(file_, xchannel, ychannel, nxbins=1024, nybins=1024, chunk_size=1000000):
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
            binned = np.transpose(binned.compute())

    cmap = copy(plt.cm.plasma)
    cmap.set_under("w", 0)
    cmap.set_over("w", 0)
    fig, ax = plt.subplots()
    img = ax.imshow(
        binned,
        norm=mpc.LogNorm(vmin=1, vmax=binned.max()),
        interpolation=None,
        origin="lower",
        cmap=cmap,
        extent=(xmin, xmax, ymin, ymax)
    )
    cbar = fig.colorbar(img, ax=ax)
    cbar.set_label("Counts")
    ax.set(
        xlabel=xchannel,
        ylabel=ychannel
    )
    plt.tight_layout()
    return fig

# def hist2d_from_mpa_data(file_, xchannel, ychannel, nxbins=1024, nybins=1024, chunk_size=1000000):
#     with h5py.File(file_, "r") as f:
#         config = f["CFG"]
#         xmin = 0
#         ymin = 0
#         try:
#             xmax = config[xchannel].attrs["range"]
#         except:
#             xmax = INVALID_ADC_VALUE
#         try:
#             ymax = config[ychannel].attrs["range"]
#         except:
#             ymax = INVALID_ADC_VALUE
#         events = f["EVENTS"]
#         n = events["TIME"].len()
#         binned = np.zeros((nybins, nxbins))
#         for k in tqdm(range(n//chunk_size+1), desc="Processing"):
#             if (k+1)*chunk_size + 1 < n:
#                 a = events[xchannel][k*chunk_size:(k+1)*chunk_size + 1]
#                 b = events[ychannel][k*chunk_size:(k+1)*chunk_size + 1]
#             else:
#                 a = events[xchannel][k*chunk_size:]
#                 b = events[ychannel][k*chunk_size:]
#             ex, ey, b = hist2d(a, xmin, xmax, nxbins, b, ymin, ymax, nybins)
#             binned += b

#     cmap = copy(plt.cm.plasma)
#     cmap.set_under("w", 0)
#     cmap.set_over("w", 0)
#     fig, ax = plt.subplots()
#     img = ax.imshow(
#         binned,
#         norm=mpc.LogNorm(vmin=1, vmax=binned.max()),
#         interpolation=None,
#         origin="lower",
#         cmap=cmap,
#         extent=(xmin, xmax, ymin, ymax)
#     )
#     cbar = fig.colorbar(img, ax=ax)
#     cbar.set_label("Counts")
#     ax.set(
#         xlabel=xchannel,
#         ylabel=ychannel
#     )
#     plt.tight_layout()
#     return fig

# def hist1d_from_mpa_data(file_, xchannel, nxbins=1024, chunk_size=1000000):
#     with h5py.File(file_, "r") as f:
#         config = f["CFG"]
#         xmin = 0
#         try:
#             xmax = config[xchannel].attrs["range"]
#         except:
#             xmax = INVALID_ADC_VALUE
#         events = f["EVENTS"]
#         n = events["TIME"].len()
#         binned = np.zeros(nxbins)
#         for k in tqdm(range(n//chunk_size+1), desc="Processing"):
#             if (k+1)*chunk_size + 1 < n:
#                 a = events[xchannel][k*chunk_size:(k+1)*chunk_size + 1]
#             else:
#                 a = events[xchannel][k*chunk_size:]
#             ex, b = hist1d(a, xmin, xmax, nxbins)
#             binned += b

#     fig, ax = plt.subplots()
#     # plt.bar(ex, binned, align="edge", width=ex[1]-ex[0], fill=False)
#     ax.step(ex, binned, where='post')
#     ax.set(
#         xlabel=xchannel,
#         ylabel="Counts",
#         yscale="log",
#     )
#     plt.tight_layout()
#     return fig

def hist1d_from_mpa_data(file_, xchannel, nxbins=1024, chunk_size=1000000):
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

    fig, ax = plt.subplots()
    ax.step(ex[:-1], binned, where='post')
    ax.set(
        xlabel=xchannel,
        ylabel="Counts",
        yscale="log",
    )
    plt.tight_layout()
    return fig

def _parse_cli_args():
    parser = argparse.ArgumentParser(
        description="Make a histogram from MPA data in HDF5 format."
    )
    parser.add_argument(
        "file",
        help="The data file.",
        type=str,
    )
    parser.add_argument(
        "xchannel",
        help="Channel to plot on the x-axis, e.g. ADC0, ADC1, ....",
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
        help="Channel to plot on the y-axis, forces 2D-histogram.",
        type=str,
        default=""
    )
    parser.add_argument(
        "--ny",
        help="Number of bins on the y-axis.",
        type=int,
        default=1024,
    )
    parser.add_argument(
        "-o",
        "--output",
        help="The designated output file name.",
        type=str,
        default=""
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
    if not os.path.isfile(args.file):
        sys.exit("The specified file could not be found.")
    save_as = {
        ".pdf":args.pdf,
        ".pgf":args.pgf,
        ".png":args.png,
        ".eps":args.eps,
    }
    if args.output:
        out_name, ext = os.path.splitext(args.output)
        if ext:
            save_as[ext] = True
    else:
        out_name, _ = os.path.splitext(args.file)

    if not any(save_as.values()):
        save_as[".pdf"] = True

    if not args.ychannel:
        _fig = hist1d_from_mpa_data(args.file, args.xchannel, nxbins=args.nx)
    else:
        _fig = hist2d_from_mpa_data(args.file, args.xchannel, args.ychannel, nxbins=args.nx, nybins=args.ny)

    for ext, do_save in save_as.items():
        if do_save:
            plt.savefig(out_name + ext)


    sys.exit(0)

if __name__ == "__main__":
    _main()
