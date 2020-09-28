import os
from copy import copy

import numpy as np
import h5py

import matplotlib.pyplot as plt
import matplotlib.colors as mpc

from _common import (
    PLOT_LABEL_ADC_TO_PHYS,
)


class Histogram:
    def __init__(self, counts, ex, ey=None, attrs=None, meta=None):
        self.counts = counts
        self.ex = ex
        self.ey = ey
        self.attrs = attrs
        self.meta = meta or {}

        self.cx = (ex[:-1] + ex[1:])/2
        if self.ey is not None:
            self.cy = (ey[:-1] + ey[1:])/2

        if self.meta:
            self.pex = self.scale_adc2phys(self.ex, axis="x")
            self.pcx = (self.pex[:-1] + self.pex[1:])/2

            if self.ey is not None:
                self.pey = self.scale_adc2phys(self.ey, axis="y")
                self.pcy = (self.pey[:-1] + self.pey[1:])/2
        else:
            self.pex = self.pcx = self.pey = self.pcy = None

    @classmethod
    def from_h5hist(cls, file_, metafile=None):
        with h5py.File(file_, "r") as f:
            attrs = {k:v for k, v in f.attrs.items()}
            ex = f["EX"][:]
            if attrs.get("kind", "1D") == "2D":
                ey = f["EY"][:]
            else:
                ey = None
            counts = f["HIST"][:]
        if metafile is None:
            meta = None
        else:
            from pickle import load
            with open(metafile, "rb") as f:
                meta = load(f)
        return cls(counts, ex, ey=ey, attrs=attrs, meta=meta)

    def scale_adc2phys(self, arr, axis):
        if axis == "x":
            adc = self.attrs["xchannel"]
        elif axis == "y":
            adc = self.attrs["ychannel"]
        m = (self.meta[adc + "_CALIB_HIGH"] - self.meta[adc + "_CALIB_LOW"])/\
            (self.meta[adc + "_CUT_HIGH"] - self.meta[adc + "_CUT_LOW"])
        scaled = m*(arr - self.meta[adc + "_CUT_LOW"]) + self.meta[adc + "_CALIB_LOW"]
        return scaled

    def scale_phys2adc(self, arr, axis):
        if axis == "x":
            adc = self.attrs["xchannel"]
        elif axis == "y":
            adc = self.attrs["ychannel"]
        m = (self.meta[adc + "_CALIB_HIGH"] - self.meta[adc + "_CALIB_LOW"])/\
            (self.meta[adc + "_CUT_HIGH"] - self.meta[adc + "_CUT_LOW"])
        scaled = (arr - self.meta[adc + "_CALIB_LOW"])/m + self.meta[adc + "_CUT_LOW"]
        return scaled

    def plot(self, *args, **kwargs):
        if self.ey is not None:
            return hist2d(self, *args, **kwargs)
        return hist1d(self, *args, **kwargs)

    def cropped(self, x_lower_idx=None, x_upper_idx=None, y_lower_idx=None, y_upper_idx=None):
        ex = self.ex[x_lower_idx:x_upper_idx+1]
        counts = self.counts[x_lower_idx:x_upper_idx]
        if self.ey is not None:
            ey = self.ey[y_lower_idx:y_upper_idx+1]
            counts = counts[:, y_lower_idx:y_upper_idx]
        else:
            ey = None
        return self.__class__(counts.copy(), ex.copy(), ey=ey.copy(), attrs=self.attrs.copy())




def hist2d(histogram, scaling="log", ax=None, vmin=1, vmax=None, clabel=True):
    ex = histogram.ex
    ey = histogram.ey
    counts = histogram.counts

    cmap = copy(plt.cm.plasma)
    cmap.set_under("w", 0)
    # cmap.set_over("w", 0)

    if vmax is None:
        vmax = counts.max()

    if ax is None:
        fig, ax = plt.subplots()
    else:
        fig = ax.figure

    if scaling == "log":
        norm = mpc.LogNorm(vmin=vmin, vmax=vmax)
    elif scaling == "linear":
        norm = mpc.Normalize(vmin=vmin, vmax=vmax)
    if counts.max() > 0:
        img = ax.imshow(
            counts.T,
            norm=norm,
            interpolation=None,
            origin="lower",
            cmap=cmap,
            extent=(ex.min(), ex.max(), ey.min(), ey.max())
        )
    ax.set(
        xlabel=histogram.attrs["xchannel"],
        ylabel=histogram.attrs["ychannel"]
    )
    if histogram.meta:
        xfun = lambda x: histogram.scale_adc2phys(x, "x")
        xinv = lambda x: histogram.scale_adc2phys(x, "x")
        yfun = lambda y: histogram.scale_adc2phys(y, "y")
        yinv = lambda y: histogram.scale_adc2phys(y, "y")
        sax = ax.secondary_xaxis("top", functions=(xfun, xinv))
        say = ax.secondary_yaxis("right", functions=(yfun, yinv))
        sax.set_xlabel(PLOT_LABEL_ADC_TO_PHYS[histogram.attrs["xchannel"]])
        say.set_ylabel(PLOT_LABEL_ADC_TO_PHYS[histogram.attrs["ychannel"]])
    cbar = fig.colorbar(img, ax=ax, extend="max", pad=0.15)
    if clabel:
        cbar.set_label("Counts")

    plt.tight_layout()
    return fig

def hist1d(histogram, scaling="log", ax=None):
    if ax is None:
        fig, ax = plt.subplots()
    else:
        fig = ax.figure
    ax.step(histogram.ex[:-1], histogram.counts, where='post')
    ax.set(
        xlabel=histogram.attrs["xchannel"],
        ylabel="Counts",
        yscale=scaling,
    )
    if histogram.meta:
        xfun = lambda x: histogram.scale_adc2phys(x, "x")
        xinv = lambda x: histogram.scale_adc2phys(x, "x")
        sax = ax.secondary_xaxis("top", functions=(xfun, xinv))
        sax.set_xlabel(PLOT_LABEL_ADC_TO_PHYS[histogram.attrs["xchannel"]])
    plt.tight_layout()
    return fig
