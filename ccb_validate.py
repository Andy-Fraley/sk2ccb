#!/usr/bin/env python

import sys, os.path, csv, argparse, petl, re, datetime, shutil, tempfile


def main(argv):

    parser = argparse.ArgumentParser()
    parser.add_argument("--input-ccb-csv-filename", required=True, help="Input CCB CSV loading file to validate")
    parser.add_argument("--output-validation-csv-filename", required=True, help="Output CSV file that'll be created " \
        "with validation results")
    args = parser.parse_args()

    table = petl.fromcsv(args.input_ccb_csv_filename)

    constraints = [
        {'name': 'max_len_20', 'field':'Legal Name', 'assertion':max_len(20)},
        {'name': 'max_len_30', 'field':'How They Heard', 'assertion':max_len(30)},
        {'name': 'max_len_20', 'field':'Last Name', 'assertion':max_len(20)},
        {'name': 'max_len_100', 'field':'Mailbox Number', 'assertion':max_len(100)},
        {'name': 'max_len_20', 'field':'Middle Name', 'assertion':max_len(20)},
        {'name': 'max_len_30', 'field':'Job Title', 'assertion':max_len(30)},
        {'name': 'max_len_20', 'field':'First Name', 'assertion':max_len(20)},
        {'name': 'max_len_30', 'field':'School', 'assertion':max_len(30)},
        {'name': 'max_len_semisep_30', 'field':'Abilities/Skills', 'assertion':max_len_semisep(30)},
        {'name': 'max_len_semisep_30', 'field':'Spiritual Gifts', 'assertion':max_len_semisep(30)},
        {'name': 'max_len_semisep_30', 'field':'Passions', 'assertion':max_len_semisep(30)},
        {'name': 'max_len_100', 'field':'Transferred Frm', 'assertion':max_len(100)},
        {'name': 'max_len_100', 'field':'Transferred To', 'assertion':max_len(100)},
        {'name': 'max_len_30', 'field':'How They Joined', 'assertion':max_len(30)},
        {'name': 'max_len_30', 'field':'Membership Type', 'assertion':max_len(30)},
        {'name': 'max_len_30', 'field':'Reason Left Church', 'assertion':max_len(30)},
        {'name': 'max_len_100', 'field':'Pastr When Join', 'assertion':max_len(100)},
        {'name': 'max_len_100', 'field':'Pastr When Leav', 'assertion':max_len(100)}
    ]

    validation_table = petl.validate(table, constraints=constraints)
    validation_table.tocsv(args.output_validation_csv_filename)

    # Flush to ensure all output is written
    sys.stdout.flush()
    sys.stderr.flush()


def max_len(num):
    return lambda x: max_len_checker(x, num)


def max_len_checker(x, num):
    if not len(x) <= num:
        prefix = '***'
    else:
        prefix = ''
    print prefix + " max_len_checker('" + str(x) + "', " + str(num) + ')=' + str(len(x) <= num)
    return len(x) <= num


def max_len_semisep(num):
    return lambda x: max_len_semisep_checker(x, num)


def max_len_semisep_checker(x, num):
    max_len = 0
    for field in x.split(';'):
        field = field.strip()
        print "max_len_semisep_checker('" + str(field) + "', " + str(num) + ')=' + str(len(field) <= num)
        if max_len < len(field):
            max_len = len(field)
    return max_len <= num


if __name__ == "__main__":
    main(sys.argv[1:])
