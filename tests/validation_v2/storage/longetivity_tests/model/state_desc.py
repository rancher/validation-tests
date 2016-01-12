import os

from . import mutations

class StateDesc:
    def __init__(self, dev, dev_size, w_size):
        self.fd = os.open(dev, os.O_RDWR | os.O_SYNC)
        self._mutations = mutations.MutationTable(dev_size)
        self.w_size = w_size

    def apply_mutations(self, muts):
        self._mutations.apply_mutations(muts, self.w_size)

    def get_model_state(self, start, size):
        return self._mutations.get_model_state(start, size)

    def get_maximum_block(self):
        return self._mutations.get_maximum_block()

    def clear(self):
        os.close(self.fd)
