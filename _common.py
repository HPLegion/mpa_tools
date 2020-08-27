import os
import sys

import argparse

from dask.callbacks import Callback
from tqdm.auto import tqdm

INVALID_ADC_VALUE = 65535 #essentially -1 for uint16
LST_FILE_APPROX_CHUNK = 50_000_000
TYPICAL_DASK_CHUNK = 1_000_000

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