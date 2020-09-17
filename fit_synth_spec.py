import sys
import os

import argparse

import numpy as np
import numba as nb
import h5py

from scipy.optimize import curve_fit

from tqdm import tqdm

import ebisim as eb

from _common import (
    running_avg,
    running_std,
    squeeze_array
)

_BG_MIN = 0
_BG_MAX = 1000

_DELTA_EKIN_MIN = -200
_DELTA_EKIN_MAX = 50

_FWHM_MIN = 0.5
_FWHM_MAX = 80

_W_HE_MIN = 0
_W_HE_MAX = 250

_W_LI_MIN = 0
_W_LI_MAX = 250

_W_BE_MIN = 0
_W_BE_MAX = 250

_W_B_MIN = 0
_W_B_MAX = 250

_W_C_MIN = 0
_W_C_MAX = 250

_W_N_MIN = 0
_W_N_MAX = 250

_W_O_MIN = 0
_W_O_MAX = 250


_XS_SCALING = 1.e24
_FE = eb.get_element(26)
@nb.njit
def synth_fe_spec(ekin, bg, delta_ekin, fwhm, w_he, w_li, w_be, w_b, w_c, w_n, w_o):
    drxs = eb.xs.drxs_energyscan(_FE, fwhm, ekin + delta_ekin)[1]  * _XS_SCALING
    he = w_he * drxs[-3]
    li = w_li * drxs[-4]
    be = w_be * drxs[-5]
    b = w_b * drxs[-6]
    c = w_c * drxs[-7]
    n = w_n * drxs[-8]
    o = w_o * drxs[-9]
    return (he + li + be + b + c + n + o) + bg

_EPS = 0.01
@nb.njit
def synth_fe_spec_jac(ekin, bg, delta_ekin, fwhm, w_he, w_li, w_be, w_b, w_c, w_n, w_o):
    drxs = eb.xs.drxs_energyscan(_FE, fwhm, ekin + delta_ekin)[1]  * _XS_SCALING
    jac = np.zeros((ekin.size, 10))
    jac[:, 0] = 1
    jac[:, 1] = ((
            synth_fe_spec(ekin, bg, delta_ekin+_EPS, fwhm, w_he, w_li, w_be, w_b, w_c, w_n, w_o)
            - synth_fe_spec(ekin, bg, delta_ekin, fwhm, w_he, w_li, w_be, w_b, w_c, w_n, w_o)
        )/_EPS
    )
    jac[:, 2] = ((
            synth_fe_spec(ekin, bg, delta_ekin, fwhm+_EPS, w_he, w_li, w_be, w_b, w_c, w_n, w_o)
            - synth_fe_spec(ekin, bg, delta_ekin, fwhm, w_he, w_li, w_be, w_b, w_c, w_n, w_o)
        )/_EPS
    )
    jac[:, 3] = drxs[-3]
    jac[:, 4] = drxs[-4]
    jac[:, 5] = drxs[-5]
    jac[:, 6] = drxs[-6]
    jac[:, 7] = drxs[-7]
    jac[:, 8] = drxs[-8]
    jac[:, 9] = drxs[-9]
    return jac


_LOWER_BOUND = np.array([
    _BG_MIN, _DELTA_EKIN_MIN, _FWHM_MIN,
    _W_HE_MIN, _W_LI_MIN, _W_BE_MIN, _W_B_MIN, _W_C_MIN, _W_N_MIN, _W_O_MIN
])
_UPPER_BOUND = np.array([
    _BG_MAX, _DELTA_EKIN_MAX, _FWHM_MAX,
    _W_HE_MAX, _W_LI_MAX, _W_BE_MAX, _W_B_MAX, _W_C_MAX, _W_N_MAX, _W_O_MAX
])
_DEFAULT_INIT_GUESS = np.array([
    1, -50, 25,
    10, 10, 10, 10, 10, 10, 10
])
def fit_synth_fe_spec(bin_centers, hist, hist_err=None, p0=None, plb=None, pub=None):
    p0 = p0 if p0 is not None else _DEFAULT_INIT_GUESS
    plb = plb if plb is not None else _LOWER_BOUND
    pub = pub if pub is not None else _UPPER_BOUND

    popt, pcov = curve_fit(
        synth_fe_spec,
        bin_centers,
        hist,
        sigma=hist_err,
        absolute_sigma=True,
        p0=p0,
        bounds=(plb, pub),
        jac=synth_fe_spec_jac,
    )

    return popt, np.sqrt(np.diag(pcov))

def mc_fit_synth_fe_spec(bin_centers, hist, hist_err=None, niter=25, plb=None, pub=None):
    plb = plb if plb is not None else _LOWER_BOUND
    pub = pub if pub is not None else _UPPER_BOUND

    popts = []
    pstds = []
    for k in range(niter):
        try:
            p0 = np.random.random_sample(plb.shape) * (pub - plb) + plb
            popt, pstd = fit_synth_fe_spec(bin_centers, hist, hist_err=hist_err, p0=p0, plb=plb, pub=pub)
            popts.append(popt)
            pstds.append(pstd)
        except RuntimeError:
            pass

    popts = np.asarray(popts)
    psdts = np.asarray(pstds)

    ws = 1/(psdts**2)

    popt = np.sum(popts * ws, axis=0)/np.sum(ws, axis=0)
    pstd = np.sqrt(np.sum(ws*(popts-popt)**2, axis=0)/np.sum(ws, axis=0))

    return popt, pstd




def simple_correlation_estimate_delta_ekin(e_kin, hist):
    mdl = np.sum(eb.xs.drxs_energyscan(_FE, 2*(e_kin[1]-e_kin[0]), e_kin)[1], axis=0)
    mdl = (mdl - mdl.mean())/np.std(mdl)
    des = np.zeros(hist.shape[1])
    for k in tqdm(range(hist.shape[1]), desc="dE Estimation"):
        slice_ = hist[:, k:(k+1)].mean(axis=-1)
        slice_ = (slice_ - slice_.mean())/np.std(slice_)

        corr = np.correlate(slice_, mdl, mode="full")/slice_.shape[0]

        idx = corr.argmax() - (e_kin.size - 1)
        des[k] = e_kin[0] - e_kin[idx]
    return des

def sum_and_shrink_2d(data, rows, cols): # https://stackoverflow.com/questions/10685654/reduce-resolution-of-array-through-summation
    return data.reshape(rows, data.shape[0]//rows, cols, data.shape[1]//cols).sum(axis=1).sum(axis=2)

# def correlation_estimate_delta_ekin(e_kin, hist):
#     Fe = eb.get_element(26)
#     mdl = np.sum(eb.xs.drxs_energyscan(Fe, 2*(e_kin[1]-e_kin[0]), e_kin)[1], axis=0)
#     mdl = (mdl - mdl.mean())/np.std(mdl)
#     pkss = []
#     for k in tqdm(range(hist.shape[1]), desc="dE Estimation"):
#         slice_ = hist[:, k:(k+1)].mean(axis=-1)
#         slice_ = (slice_ - slice_.mean())/np.std(slice_)

#         corr = np.correlate(slice_, mdl, mode="full")/slice_.shape[0]
#         corr[:mdl.size//2] = 0
#         corr[3*mdl.size//2:] = 0
#         corr = np.maximum(corr, 0)

#         pks = find_peaks_cwt(corr, np.arange(10, 30))
#         idx = np.argsort(-corr[pks.astype(int)])
#         pks = pks[idx]
#         _des = []
#         _pks = np.full(3, -1)
#         _pks[:np.minimum(3, pks.size)] = pks[:3]
#         pkss.append(_pks)

#     pkss = np.vstack(pkss)

#     fil = np.abs(np.convolve(pkss[:,0], np.array([0,-0.5, 1, -0.5, 0]), mode="same")) > 5
#     chng = np.argwhere(np.diff(fil))
#     run = np.diff(chng.T)
#     lower = int(chng[np.argmax(run)])
#     upper = int(chng[np.argmax(run)+1])

#     p = np.zeros(pkss.shape[0])
#     p[lower:upper] = pkss[lower:upper, 0]
#     for k in range(lower-1, -1, -1):
#         p[k] = pkss[k, np.argmin(np.abs(pkss[k, :]-p[k+1]))]
#     for k in range(upper+1, p.size):
#         p[k] = pkss[k, np.argmin(np.abs(pkss[k, :]-p[k-1]))]
#     p -= (e_kin.size-1)
#     p = p.astype(int)
#     p = np.maximum(0, p)
#     p = np.minimum(e_kin.size-1, p)
#     return e_kin[0]-e_kin[p]

def bisection_fit(e_kin, hist, n=2, progbar=None):
    nr = hist.shape[1]
    hist_poisson_err = np.sqrt(hist) + 1

    if progbar is None:
        cleanup_needed = True
        progbar = tqdm(total=nr)
    else:
        cleanup_needed = False
        progbar.total = progbar.total + nr
        progbar.refresh()

    if nr == 1:
        ## Fit and return
        popts, pstds = fit_synth_fe_spec(e_kin, hist[:,0], hist_err=hist_poisson_err[:, 0])
        progbar.update()
        return np.atleast_2d(popts), np.atleast_2d(pstds)


    # Else get starting value from lower resolution fits
    compressed = squeeze_array(hist, n=n, axis=1)
    p0s, _ = bisection_fit(e_kin, compressed, n=n, progbar=progbar)

    # fit and return
    popts = np.full((nr, 10), np.nan)
    pstds = np.full((nr, 10), np.nan)

    for k in range(nr):
        p0 = p0s[k//n, :]
        p0 = np.minimum(p0, _UPPER_BOUND)
        p0 = np.maximum(p0, _LOWER_BOUND)
        try:
            popt, pstd = fit_synth_fe_spec(e_kin, hist[:, k], hist_err=hist_poisson_err[:, k], p0=p0)
            popts[k] = popt
            pstds[k] = pstd
        except RuntimeError:
            pass
        progbar.update()
    if cleanup_needed:
        progbar.close()
    return popts, pstds



def fit_overview_plot(histogram, synth_histogram, popts, pstds):
    fig, axs = plt.subplots(3,2, figsize=(7, 8))

    histogram.plot(ax = axs[0, 0], vmin=0.1,vmax=histogram.counts.max(), clabel=False)
    axs[0, 0].set_title("Data")

    synth_histogram.plot(ax = axs[0, 1], vmin=0.1, vmax=histogram.counts.max(), clabel=False)
    axs[0, 1].set_title("Fit")

    # markers, caps, bars = axs[1, 0].errorbar(t, popts[:, 0], pstds[:, 0], fmt=".", ms=1, lw=1)
    # for b in bars: b.set_alpha(0.5)
    axs[1, 0].plot(t, popts[:, 0], ".")
    axs[1, 0].fill_between(t, popts[:, 0]-pstds[:, 0], popts[:, 0]+pstds[:, 0], alpha=0.5)
    axs[1, 0].set(
        ylabel="Background (a.u.)",
        xlim=(-.5, t.max()+.5),
        ylim=(0, 1.2*np.percentile(popts[:, 0], 95))
    )

    for k, lbl in zip(range(3, 10), ["He", "Li", "Be", "B", "C", "N", "O"]):
        axs[1, 1].plot(t, popts[:, k], ".", label=lbl)
        axs[1, 1].fill_between(t, popts[:, k]-pstds[:, k], popts[:, k]+pstds[:, k], alpha=0.5)
    axs[1, 1].legend(fontsize="x-small")
    axs[1, 1].set(
        ylabel="Abundance (a.u.)",
        xlim=(-.5, t.max()+.5),
        ylim=(0, 1.2*np.percentile(popts[:, 3:], 95)),
    )

    # axs[2, 0].errorbar(t, popts[:, 1], pstds[:, 1], fmt=".")
    axs[2, 0].plot(t, popts[:, 1], ".")
    axs[2, 0].fill_between(t, popts[:, 1]-pstds[:, 1], popts[:, 1]+pstds[:, 1], alpha=0.5)
    axs[2, 0].set(
        ylabel="Space charge (V)",
        xlabel="Time (s)",
        xlim=(-.5, t.max()+.5),
        ylim=(1.2*np.percentile(popts[:, 1], 5), 0),
    )

    # axs[2, 1].errorbar(t, popts[:, 2], pstds[:, 2], fmt=".")
    axs[2, 1].plot(t, popts[:, 2], ".")
    axs[2, 1].fill_between(t, popts[:, 2]-pstds[:, 2], popts[:, 2]+pstds[:, 2], alpha=0.5)
    axs[2, 1].set(
        ylabel="FWHM (eV)",
        xlabel="Time (s)",
        xlim=(-.5, t.max()+.5),
        ylim=(0, 1.2*np.percentile(popts[:, 2], 95))
    )
    plt.tight_layout()

    return fig