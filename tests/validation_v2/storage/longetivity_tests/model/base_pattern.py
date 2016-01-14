import struct
import os
import math

class BasePattern:    
    __padding__ = ''

    def __init__(self, state_desc):
        self._state_desc = state_desc
        if self.__padding__ == '':
            for i in xrange(0, 4088):
                # write 4088 bytes (intended as padding after writing 64 bits of one block,
                # cos u've already written 8 bytes (64-bit unique identifier))
                # this way you created a 4kb block (4096 bytes)
                self.__class__.__padding__ += struct.pack('=?', 0)

    def _get_actual_state(self, start, size):
        os.lseek(self._state_desc.fd, start * 4096, os.SEEK_SET)
        blocks = []
        for i in xrange(0, size):
            block = os.read(self._state_desc.fd, 4096)
            blocks.append(struct.unpack('=Q', block[0:8])[0])
        return blocks

    def _mutate_disk(self, muts):
        for mut in muts:
            os.lseek(self._state_desc.fd, mut.start * 4096, os.SEEK_SET)
            start_val = mut.start_val
            for i in xrange(0, int(math.floor(mut.size/self._state_desc.w_size))):
                chunk = self._get_unique_blocks(start_val, self._state_desc.w_size)
                start_val += self._state_desc.w_size
                # should I validate that every write succeeds?
                os.write(self._state_desc.fd, chunk)
            # remainder chunk
            chunk = self._get_unique_blocks(start_val, (mut.size % self._state_desc.w_size))
            os.write(self._state_desc.fd, chunk)
   
    def _get_unique_blocks(self, start_val, num_blocks):
        blocks = ''
        for val in xrange(start_val, start_val + num_blocks):
            block = struct.pack('=Q', val) # the start of the block contains a 64-bit unsigned number, to uniquely identify it
            block += self.__padding__
            blocks += block
        return blocks

    def mutate_and_verify(self):
        muts = self._mutate()
        return self._verify(muts)

    def _mutate(self):
        muts = self._compute_mutations()
        # print 'Applying: Mutation Set => [', ','.join(m.__str__() for m in muts), ']'
        self._state_desc.apply_mutations(muts)
        self._mutate_disk(muts)
        return muts

    def _verify(self, muts):
        for mut in muts:
            size_to_read = 16 if mut.size >=16 else mut.size
            
            # check start blocks of each mutation
            expected_state = self._state_desc.get_model_state(mut.start, size_to_read)
            new_state = self._get_actual_state(mut.start, size_to_read)
            if not self._compare_blocks(expected_state, new_state):
                print 'ERROR DETECTED in span start: Mutation Set => [', ','.join(m.__str__() for m in muts), ']'
                print 'ERROR IN START=%s'%mut.start, 'SIZE=%s'%mut.size
                print 'EXPECTED=%s'%expected_state, 'FOUND=%s'%new_state
                return False
            
            end = mut.start + mut.size
            # check end blocks of each mutation
            expected_state = self._state_desc.get_model_state(end - size_to_read, size_to_read)
            new_state = self._get_actual_state(end - size_to_read, size_to_read)
            if not self._compare_blocks(expected_state, new_state):
                print 'ERROR DETECTED in span end: Mutation Set => [', ','.join(m.__str__() for m in muts), ']'
                print 'ERROR IN START=%s'%mut.start, 'SIZE=%s'%mut.size
                print 'EXPECTED=%s'%expected_state, 'FOUND=%s'%new_state
                return False
            
            if end + size_to_read < self._state_desc.get_maximum_block():
                # check border blocks just after the end of each mutation
                expected_state = self._state_desc.get_model_state(end, size_to_read)
                new_state = self._get_actual_state(end, size_to_read)
                if not self._compare_blocks(expected_state, new_state):
                    print 'ERROR DETECTED in gap: Mutation Set => [', ','.join(m.__str__() for m in muts), ']'
                    print 'ERROR IN START=%s'%mut.start, 'SIZE=%s'%mut.size
                    print 'EXPECTED=%s'%expected_state, 'FOUND=%s'%new_state
                    return False
        return True
        
    def _compare_blocks(self, expected, actual):
        if len(expected) != len(actual):
            return False
        for i in range(0, len(expected)):
            if expected[i] != actual[i]:
                return False
        return True
