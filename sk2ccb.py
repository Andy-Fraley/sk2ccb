#!/usr/bin/python

import sys, getopt

def main(argv):

    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--contribution-filename", required=True, nargs='+', action='append', \
        help="'Contribution' filename (input CSV file)")
    parser.add_argument("--individual-filename",  required=True, nargs='+', action='append', \
        help="'Individual' filename (input CSV file)")
    parser.add_argument("--family-filename",  required=True, nargs='+', action='append', \
        help="'Family' filename (input CSV file)")
    parser.add_argument("--output-filename",  required=True, help="'Output' filename (output XLS file)")
    args = parser.parse_args()

    print str(args)

if __name__ == "__main__":
    main(sys.argv[1:])
