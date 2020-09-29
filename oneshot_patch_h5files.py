import os
import h5py
import re

# DIR = "/run/media/hpahl/HannesExSSD/Fe_DR_TimeResolvedJuly2020/"
# DIR = "."
# os.chdir(DIR)
files = os.listdir()
files = [f for f in files if "h5" in os.path.splitext(f)[1]]

# datafiles = []
for f in files:
    mtch = re.match(r"Fe_DR_(\d\d\d).*\.h5.*", f)
    if mtch:
        d = f"Fe_DR_{mtch[1]}.h5"
        with h5py.File(f, "a") as f:
            f.attrs["datafile"] = d
