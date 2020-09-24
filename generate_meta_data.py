import sys
import os
import pickle

import argparse

from _common import(
    default_argparser,
    read_orchestration_csv,
    check_input,
    check_output
)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Extract metadata from orchestration file and save as pickle object.",
        parents=[default_argparser],
    )
    parser.add_argument(
        "lst",
        type=str,
        help="Filename corresponding to lst file"
    )

    args = parser.parse_args()

    if not args.out:
        out = args.lst[:-4] + ".meta"
    else:
        out = args.out

    check_input(args.file)
    check_output(out, yes=args.yes)

    df = read_orchestration_csv(args.file)
    df = df.set_index("FILE")

    with open(out, "wb") as f:
        pickle.dump(dict(df.loc[args.lst]), f)

    sys.exit(0)