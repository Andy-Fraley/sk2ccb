#!/usr/bin/env python


import sys, getopt, os.path, csv, argparse, petl


def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument("--individuals-filename", required=True, help="Input CSV with individuals data dumped " \
                        "from Servant Keeper")
    parser.add_argument("--child-approvals-filename", required=True, help="Filename of CSV file listing approval " \
                        "dates that individuals got various clearances to work with children")
    parser.add_argument("--output-filename", required=True, help="Output CSV filename which will be loaded with " \
                        "individuals data in CCB import format ")
    args = parser.parse_args()

    if not os.path.isfile(args.individuals_filename):
        print >> sys.stderr, "Error: cannot open file '" + args.individuals_filename + "'"
        sys.exit(1)

    individuals_input_table = petl.fromcsv(args.individuals_filename)
    individuals_output_table = petl.empty()

    individuals_output_table = transform_rename_rows(individuals_input_table, individuals_output_table)

    print
    print individuals_output_table


def transform_rename_rows(individuals_input_table, individuals_output_table):
    column_mappings = {
        'Address': 'home street',
        'Address Line 2': 'home street line 2',
        'Address': 'mailing street',
        'Address Line 2': 'mailing street line 2',
        'Alt Address': 'other street',  # No such thing as 'other street' in silver_sample file
        'Alt Address Line 2': 'other street line 2',
        'Alt City': 'other city'
    }

    for key in column_mappings:
        individuals_output_table = petl.addcolumn(individuals_output_table, column_mappings[key], \
                                                  petl.values(individuals_input_table, key))

    return individuals_output_table


if __name__ == "__main__":
    main(sys.argv[1:])
