import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mpc
import numba as nb
import h5py
from tqdm import tqdm


@nb.njit(cache=True, parallel=True)
def index_data(data, dmin, dmax, nbins):
    m = (nbins-1)/(dmax - dmin)
    b = -m*dmin
    idx = np.zeros_like(data, dtype=np.int32)
    idx[:] = m * data + b
    idx = np.minimum(idx, nbins-1)
    # idxi = idx.astype(np.int)
    edges = (np.arange(nbins)-b)/m
    return edges, idx

@nb.njit(cache=True, parallel=True)
def hist1d(data, dmin, dmax, nbins):
    edges, idx = index_data(data, dmin, dmax, nbins)
    binned = np.zeros(nbins, dtype=np.int32)
    for i in idx:
        binned[i] += 1
    return edges, binned

@nb.njit(cache=True, parallel=True)
def hist2d(datax, dxmin, dxmax, nxbins, datay, dymin, dymax, nybins):
    ex, ix = index_data(datax, dxmin, dxmax, nxbins)
    ey, iy = index_data(datay, dymin, dymax, nybins)
    binned = np.zeros((nxbins, nybins), dtype=np.int32)
    for x, y in zip(ix, iy):
        binned[x, y] += 1
    return ex, ey, binned


with h5py.File("./Fe_DR_019.h5") as f:
    events = f["EVENTS"]
    n = events["TIME"].len()
    CHNKSZ = 1000000
    binned = np.zeros((512, 512))
    for k in tqdm(range(n//CHNKSZ+1)):
        if (k+1)*CHNKSZ + 1 < n:
            a = events["ADC0"][k*CHNKSZ:(k+1)*CHNKSZ + 1]
            b = events["ADC1"][k*CHNKSZ:(k+1)*CHNKSZ + 1]
        else:
            a = events["ADC0"][k*CHNKSZ:]
            b = events["ADC1"][k*CHNKSZ:]
        ex, ey, b = hist2d(a, 0, 8192, 512, b, 0, 8192, 512)
        binned += b


# plt.bar(e, binned, align="edge", width=e[1]-e[0], fill=False)

plt.imshow(binned, norm=mpc.LogNorm(vmin=1, vmax=binned.max()), interpolation=None, origin="lower", cmap="jet")
plt.colorbar()
plt.show()