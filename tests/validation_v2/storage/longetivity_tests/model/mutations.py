class MutationTable:
    def __init__(self, dev_size):
        self._mutations = []
        self._current_state = DiskDescriptor(dev_size)

    def apply_mutations(self, mutations, w_size):
        # first argument is a list, therefore it applies a set of mutations to the current state of the model
        self._mutations.append(mutations)
        for mut in mutations:
            self._current_state.apply_mutation(mut, w_size)

    def get_model_state(self, start, size):
        return self._current_state.get_model_state(start, size)

    def get_maximum_block(self):
        return self._current_state.get_maximum_block()

class Mutation:
    #This increasing id will be the unique identifier for each block written
    __increasing_id__ = 1

    def __init__(self, start, size):
        self.start = start
        self.size = size
        self.start_val = self.__increasing_id__ 
        self.__class__.__increasing_id__ += size

    def __str__(self):
        return "[start = " + str(self.start) + ", size = " + str(self.size) + ", start_val = " + str(self.start_val) + "]" 

class DiskDescriptor:
    def __init__(self, dev_size):
        self._dev_size = int(dev_size[:-1])
        # initialize (assume) an array of 4KB blocks to serve as model
        num_4kb_blocks = self._dev_size * 262144
        self._disk = []
        for i in xrange(0, num_4kb_blocks):
            self._disk.append(0)

    def apply_mutation(self, mut, w_size):
        start_val = mut.start_val
        for i in xrange(mut.start, mut.start + mut.size):
            self._disk[i] = start_val
            start_val += 1

    def get_model_state(self, start, size):
        return self._disk[start:(start+size)]

    def get_maximum_block(self):
        return self._dev_size * 262144
