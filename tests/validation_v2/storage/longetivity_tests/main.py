#!/usr/bin/env python

import argparse
import sys

from model import state_desc
from model import large_write_pattern
from model import short_write_pattern

def _parse_args():
    parser = argparse.ArgumentParser(add_help=True)

    parser.add_argument("--device-name", help='The name of the device to write into')
    parser.add_argument("--device-size", help='The size of the specified device in G (eg. 100G)')
    parser.add_argument("--num-each-model", help='The number of times to run each model (eg. 5)')
    parser.add_argument("--num-all-models", help='The number of times to loop over all models')
    parser.add_argument("--write-size", help='The chunk size as a multiple of 4kb when performing writes')

    return parser.parse_args()

def main():
    args = _parse_args()
    dev = args.device_name
    dev_size = args.device_size
    if dev == None or dev == '':
        print 'please specify a device (using --device-name flag)'
        sys.exit(1)

    if dev_size == None or dev_size == '':
        print 'please specify the size of the device (using --device-size flag)'
        sys.exit(1)

    num_all_models = 1
    num_each_model = 2

    if args.num_all_models is not None and args.num_all_models != '':
        num_all_models = int(args.num_all_models)

    if args.num_each_model is not None and args.num_each_model != '':
        num_each_model = int(args.num_each_model)

    write_size = 1

    if args.write_size is not None and args.write_size != '':
        write_size = int(args.write_size)

    state = state_desc.StateDesc(dev, dev_size, write_size)
    
    # just append to this list to add more models
    models = [
            large_write_pattern.LargeNonOverlappingWritePattern(state),
            short_write_pattern.ShortNonOverlappingWritePattern(state),
            ]

    for i in xrange(0, num_all_models):
        for m in models:
            for j in xrange(0, num_each_model):
                if not m.mutate_and_verify():
                    state.clear()
                    print 'error while running test. exiting' #todo improve message
                    sys.exit(1)
    state.clear()

if __name__ == '__main__':
    main()
