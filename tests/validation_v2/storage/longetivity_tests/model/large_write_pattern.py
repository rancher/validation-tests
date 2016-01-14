import random

from . import mutations
from . import base_pattern

# Each write is atleast 1mb and upto a maximum of 8mb
class LargeNonOverlappingWritePattern(base_pattern.BasePattern):
    def __init__(self, state_desc):
        base_pattern.BasePattern.__init__(self, state_desc)
        self._min_span_size = 256 # number of 4kb blocks in 1mb
        self._max_span_size = 2048 # number of 4kb blocks in 8mb
        # similar params as above, but for gaps
        self._min_gap_size = 256
        self._max_gap_size = 2048
        self._disk_fill_ratio = 0.1 # the approx percentage of disk to fill

    # just overload this method of the BasePattern base class to add a new pattern
    def _compute_mutations(self):
        muts = []
        max_block_num = self._state_desc.get_maximum_block()
        max_blocks_to_write = max_block_num * self._disk_fill_ratio
        curr_start = 0
        total_written = 0
        while True:
            span_start = random.randint(curr_start, curr_start + self._max_gap_size)
            span_end = random.randint(span_start + self._min_span_size, span_start + self._max_span_size)
            # span is the region between start and end
            # gap is the region between two spans
            if span_end > max_block_num-1:
                break
            muts.append(mutations.Mutation(span_start, span_end - span_start))
            curr_start = span_end + self._min_gap_size
            total_written += (span_end - span_start)
            if total_written > max_blocks_to_write:
                break
        return muts
