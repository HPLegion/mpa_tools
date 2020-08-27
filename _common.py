from dask.callbacks import Callback
from tqdm.auto import tqdm
INVALID_ADC_VALUE = 65535 #essentially -1 for uint16

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
