import os
import sys

import argparse

import numpy as np
import numba as nb

from dask.callbacks import Callback
from tqdm.auto import tqdm

# import matplotlib.pyplot as plt

INVALID_ADC_VALUE = 65535 #essentially -1 for uint16
LST_FILE_APPROX_CHUNK = 50_000_000
TYPICAL_DASK_CHUNK = 300_000

# try:
#     plt.style.use(f"/home/hpahl/Repos/PhD-Thesis/scripts/thesis_plot.mplstyle")
# except:
#     pass


class DaskProgressBar(Callback):
    """
    See https://github.com/tqdm/tqdm/issues/278#issuecomment-649810339
    """
    def _start_state(self, dsk, state):
        self._tqdm = tqdm(
            total=sum(len(state[k]) for k in ['ready', 'waiting', 'running', 'finished']),
            desc="Processing")

    def _posttask(self, key, result, dsk, state, worker_id):
        self._tqdm.update(1)

    def _finish(self, dsk, state, errored):
        pass

default_argparser = argparse.ArgumentParser(add_help=False)
default_argparser.add_argument(
    "file",
    help="Input file.",
    type=str,
)
default_argparser.add_argument(
    "-o",
    "--out",
    help="Output file.",
    type=str,
    default=""
)
default_argparser.add_argument(
    "-y",
    "--yes",
    help="Skip yes/no prompts. WARNING May overwrite existing files.",
    action="store_true"
)

def check_input(file_):
    if not os.path.isfile(file_):
        sys.exit(f"The specified file '{file_}' could not be found.")
    return file_

def check_output(file_, yes=False):
    if os.path.isfile(file_) and not yes:
        resp = input(f"Designated output file '{file_}' already exists. Overwrite? [Y/n] ")
        if resp != "Y":
            sys.exit("Stopped due to lack of valid output file.")
    return file_

def squeeze_array(arr, n=2, axis=None):
    out = arr.copy()
    if axis == 0:
        if out.shape[0]%n:
            out = np.pad(out, ((0, n-out.shape[0]%n), (0, 0)), constant_values=np.nan)
        out = out.reshape(out.shape[0]//n, n, out.shape[1])
        out = np.nanmean(out, axis=1)
        return np.atleast_2d(out)
    if axis == 1:
        if out.shape[1]%n:
            out = np.pad(out, ((0, 0), (0, n-out.shape[1]%n)), constant_values=np.nan)
        out = out.reshape(out.shape[0], out.shape[1]//n, n)
        out = np.nanmean(out, axis=2)
        return np.atleast_2d(out)

def running_std(arr, w=1):
    @nb.stencil(neighborhood=((-w, w),))
    def kernel(a):
        mu = 0
        for i in range(-w, w+1):
            mu += a[w]
        mu /= 2*w+1
        var = 0
        for i in range(-w, w+1):
            var += (a[i] - mu)**2
        var /= 2*w+1
        return np.sqrt(var)
    res = kernel(arr)
    res[:w] = res[w+1]
    res[-w:] = res[-w-1]
    return res

def running_avg(arr, w=1):
    @nb.stencil(neighborhood=((-w, w),))
    def kernel(a):
        mu = 0
        for i in range(-w, w+1):
            mu += a[w]
        mu /= 2*w+1
        return mu
    res = kernel(arr)
    res[:w] = res[w+1]
    res[-w:] = res[-w-1]
    return res