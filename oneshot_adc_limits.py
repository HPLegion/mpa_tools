import h5py
import numpy as np
import matplotlib.pyplot as plt

# ADC2 Ee encoding - I should only have one relevant setting here
# The initial measurements had an up and down ramp -> not interesting for evaluation
# I will focus on the single ramps
# First: Fe_DR_018
# Last without mess : Fe_DR_038

# for k in range(18, 39):
#     fname = f"/run/media/hpahl/HannesExtHDD/Fe_DR_TimeResolvedJuly2020/Fe_DR_0{k}_ADC2.h5hist"
#     print(fname)
#     counts = np.zeros(1024)
#     with h5py.File(fname, "r") as f:
#         counts += f["HIST"][:]
#         ex = f["EX"][:]
# plt.plot(ex[1:]/2 + ex[:-1]/2, counts)
# plt.show()

# ADC3 time encoding - I think there should be two different relevant cases here
# 7 s / 10 s and 17 s / 20 s

for k in range(18, 39):
    fname = f"/run/media/hpahl/HannesExtHDD/Fe_DR_TimeResolvedJuly2020/Fe_DR_0{k}_ADC3.h5hist"
    print(fname)
    counts = np.zeros(1024)
    with h5py.File(fname, "r") as f:
        counts += f["HIST"][:]
        ex = f["EX"][:]
plt.plot(ex[1:]/2 + ex[:-1]/2, counts)
plt.show()

for k in range(43, 49):
    fname = f"/run/media/hpahl/HannesExtHDD/Fe_DR_TimeResolvedJuly2020/Fe_DR_0{k}_ADC3.h5hist"
    print(fname)
    counts = np.zeros(1024)
    with h5py.File(fname, "r") as f:
        counts += f["HIST"][:]
        ex = f["EX"][:]
plt.plot(ex[1:]/2 + ex[:-1]/2, counts)
plt.show()
