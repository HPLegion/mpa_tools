import argparse
from sys import stdout
import numpy as np
from _common import read_orchestration_csv

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Convert an MPA-3 list file into HDF5 format."
    )
    parser.add_argument(
        "file",
        help="The run table containing the data.",
        type=str,
    )
    args = parser.parse_args()

    df = read_orchestration_csv(args.file)
    out = " ".join(df.FILE[df.VALID)

    # with open(args.file, "r") as f:
    #     out = ""
    #     f.readline()
    #     f.readline()
    #     for line in f:
    #         line = line.split(",")
    #         if line[1].strip() == "True" and line[2].strip() == "True":
    #             out += line[0].strip() + " "

    stdout.write(out.strip()+"\n")
