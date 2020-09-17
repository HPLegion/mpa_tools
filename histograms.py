from copy import copy

import numpy as np
import h5py

import matplotlib.pyplot as plt
import matplotlib.colors as mpc


class Histogram:
    def __init__(self, counts, ex, ey=None, attrs=None):
        self.counts = counts
        self.ex = ex
        self.ey = ey
        self.attrs = attrs

        self.cx = (ex[:-1] + ex[1:])/2
        if self.ey is not None:
            self.cy = (ey[:-1] + ey[1:])/2

    @classmethod
    def from_h5hist(cls, file_):
        with h5py.File(file_, "r") as f:
            attrs = {k:v for k, v in f.attrs.items()}
            ex = f["EX"][:]
            if attrs.get("kind", "1D") == "2D":
                ey = f["EY"][:]
            else:
                ey = None
            counts = f["HIST"][:]
        return cls(counts, ex, ey=ey, attrs=attrs)

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
        cbar = fig.colorbar(img, ax=ax, extend="max")
        if clabel:
            cbar.set_label("Counts")
    ax.set(
        xlabel=histogram.attrs["xchannel"],
        ylabel=histogram.attrs["ychannel"]
    )
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
    plt.tight_layout()
    return fig
