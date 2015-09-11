#!/usr/bin/env python

from __future__ import print_function
import sys, os.path, csv, argparse, petl, re, datetime, shutil, tempfile


def main(argv):

    parser = argparse.ArgumentParser()
    parser.add_argument("--input-csv-filename", required=True, help="Input UTF8 CSV to summarize")
    parser.add_argument("--semi-sep-columns", required=False, nargs = '*', default=argparse.SUPPRESS,
        help="Column names of columns containing semi-colon separated values")
    parser.add_argument("--skip-columns", required=False, nargs='*', default=argparse.SUPPRESS,
        help="Column names to NOT generate stats for")
    parser.add_argument("--skip-num-rows", required=False, type=int, help="Skip specified number "
        "of header rows")
    parser.add_argument("--first-ccb-column", required=False, help="String name of first CCB column.  If "
        "specified, all preceeding columns will be labeled 'Servant Keeper' and this column "
        "and all subsequent will be labeled 'CCB'")
    args = parser.parse_args()

    if args.first_ccb_column is not None:
        column_prefix = 'Servant Keeper '
    else:
        column_prefix = ''

    assert os.path.isfile(args.input_csv_filename), "Error: cannot open file '" + args.input_csv_filename + "'"

    table = petl.fromcsv(args.input_csv_filename)

    # Skip header rows
    if args.skip_num_rows:
        skip_num = args.skip_num_rows
        assert skip_num > 0, "--skip-num-rows value '" + str(skip_num) + "' is invalid.  Must be positive."
        it = iter(table)
        while skip_num >= 0:
            row = next(it)
            skip_num -= 1
        table = petl.setheader(table, row)
        table = petl.tail(table, petl.nrows(table) - args.skip_num_rows)

    # Print nicely formatted stats for each column
    sep = ''
    for column in petl.header(table):
        if args.first_ccb_column is not None and column == args.first_ccb_column:
            column_prefix = 'CCB '
        if args.skip_columns is None or not column in args.skip_columns:
            output_str = column_prefix + "Column '" + column + "'"
            print(sep + output_str, file=sys.stdout)
            print(output_str, file=sys.stderr)
            if args.semi_sep_columns is not None and column in args.semi_sep_columns:
                output_str = num_dict2str(dict_dump(semi_sep_valuecounter(table, column)))
                print(output_str, file=sys.stdout)
            else:
                output_str = num_dict2str(dict_dump(valuecounts(table, column)))
                print(output_str, file=sys.stdout)
        sep = '\n'


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


def dict_dump(stats_dict):
    num_dict = {}
    for key in stats_dict:
        val = stats_dict[key]
        if not val in num_dict:
            num_dict[val] = []
        num_dict[val].append(key)
    return num_dict


def num_dict2str(num_dict):
    """Format the numeric stats dictionary to a string ordered by most-occurring to least-occurring, but
    leaving '<other>' and '<blank>' for 2nd-to-last and last."""
    other_num = None
    blank_num = None
    num_dict_str = ''
    for num in sorted(num_dict, reverse=True):
        for col in sorted(num_dict[num]):
            if col == '<other>':
                other_num = num
            elif col == '<blank>':
                blank_num = num
            else:
                num_dict_str += "    '" + col + "': " + str(num) + '\n'
    if other_num is not None and other_num != 0:
        num_dict_str += "    <other>: " + str(other_num) + '\n'
    if blank_num is not None and blank_num != 0:
        num_dict_str += "    <blank>: " + str(blank_num) + '\n'
    return num_dict_str


if __name__ == "__main__":
    main(sys.argv[1:])
