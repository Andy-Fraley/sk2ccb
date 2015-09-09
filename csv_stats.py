#!/usr/bin/env python

import sys, os.path, csv, argparse, petl, re, datetime, shutil, tempfile


def main(argv):

    parser = argparse.ArgumentParser()
    parser.add_argument("--input-csv-filename", required=True, help="Input UTF8 CSV to summarize")
    parser.add_argument("--output-txt-filename", required=True, help="Output TXT filename which will have "
        "summary statistical distributions")
    parser.add_argument("--semi-sep-columns", required=False, nargs = '*', default=argparse.SUPPRESS,
        help="Column names of columns containing semi-colon separated values")
    parser.add_argument("--skip-columns", required=False, nargs='*', default=argparse.SUPPRESS,
        help="Column names to NOT generate stats for")
    args = parser.parse_args()

    assert os.path.isfile(args.input_csv_filename), "Error: cannot open file '" + args.input_csv_filename + "'"

    table = petl.fromcsv(args.input_csv_filename)

    # TODO - Rewrite this to dump out in text format, to output file, in sorted order by value (not key), where there
    # may be duplicate values
    sep = ''
    for column in petl.header(table):
        if args.skip_columns is None or not column in args.skip_columns:
            print sep + "Column: '" + column + "':"
            if args.semi_sep_columns is not None and column in args.semi_sep_columns:
                print semi_sep_valuecounter(table, column)
            else:
                print valuecounts(table, column)
        sep = '\n\n'


def semi_sep_valuecounter(table, col_name):
    dict_semi_sep = {}
    for value in petl.values(table, col_name):
        if value.strip() == '':
            continue
        else:
            for semi_sep in value.split(';'):
                semi_sep_str = semi_sep.strip()
                if semi_sep_str not in dict_semi_sep:
                    dict_semi_sep[semi_sep_str] = 0
                dict_semi_sep[semi_sep_str] += 1
    return dict_semi_sep


def valuecounts(table, col_name):
    return_dict = {}
    reported_count = 0
    unreported_count = 0
    column = petl.values(table, col_name)
    nrows = petl.nrows(table)
    non_blanks = petl.select(table, '{' + col_name + "} != ''")
    num_blanks = nrows - petl.nrows(non_blanks)
    counts_table = petl.valuecounts(non_blanks, col_name)
    for row in petl.records(counts_table):
        if row['frequency'] > 0.01:
            return_dict[row[col_name]] = row['count']
            reported_count += row['count']
        else:
            unreported_count += row['count']
    return_dict['<other>'] = unreported_count
    return_dict['<blank>'] = num_blanks
    return return_dict


if __name__ == "__main__":
    main(sys.argv[1:])
