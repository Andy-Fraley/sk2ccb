#!/usr/bin/env python


import sys, os.path, argparse, petl
from re import sub
from decimal import Decimal


def main(argv):

    parser = argparse.ArgumentParser()
    parser.add_argument("--pledges-filename", required=True, help="Input UTF8 CSV with pledges data "
        "dumped from Servant Keeper")
    parser.add_argument("--output-filename", required=True, help="Output CSV filename which will be loaded with "
        "pledges data in CCB import format ")
    parser.add_argument('--trace', action='store_true', help="If specified, prints tracing/progress messages to "
        "stdout")
    args = parser.parse_args()

    assert os.path.isfile(args.pledges_filename), "Error: cannot open file '" + args.pledges_filename + "'"

    table = petl.fromcsv(args.pledges_filename)

    table = petl.rename(table, 'Frequency', 'SK Frequency')

    table = petl.addfield(table, 'individual_id', lambda rec: rec['Individual ID'])
    table = petl.addfield(table, 'campus', 'Ingomar Church')
    table = petl.addfield(table, 'Category Pledged To', lambda rec: rec['Account'])
    table = petl.addfield(table, 'Amount Pledged', convert_amount)
    table = petl.addfield(table, 'Total Amount Pledged', lambda rec: rec['Pledged'])
    table = petl.addfield(table, 'Frequency', lambda rec: {1:'Yearly', 4:'Yearly', 12:'Monthly',
        52:'Weekly', 24:'Monthly', 2:'Yearly'}[int(rec['Payments'])])
    table = petl.addfield(table, 'Number of Gifts', lambda rec: {'Yearly':1, 'Monthly':12,
        'Weekly':52}[rec['Frequency']])
    table = petl.addfield(table, 'Length Multiplier', lambda rec: {'Yearly':'Years', 'Monthly':'Months',
        'Weekly':'Weeks'}[rec['Frequency']])
    table = petl.addfield(table, 'Start Date', lambda rec: {'Operating Income':'2013-01-01',
        'Mortgage Principal':'2013-01-01', 'Operating Income 2015':'2015-01-01'}[rec['Account']])
    table = petl.addfield(table, 'End Date', lambda rec: {'Operating Income':'2014-01-01',
        'Mortgage Principal':'2014-01-01', 'Operating Income 2015':'2016-01-01'}[rec['Account']])

    trace('CONVERTING AND THEN EMITTING TO CSV FILE...', args.trace, banner=True)

    table.progress(200).tocsv(args.output_filename)

    trace('OUTPUT TO CSV COMPLETE.', args.trace, banner=True)

    trace('DONE!', args.trace, banner=True)


def convert_amount(rec):
    multiplier = 1
    if rec['Payments'] == '4':  # Quarterly, convert to Yearly
        multiplier = 4
    elif rec['Payments'] == '24':  # Semi-monthly, convert to Monthly
        multiplier = 2
    elif rec['Payments'] == '2':  # Semi-Annually, convert to Yearly
        multiplier = 2
    return_amount = Decimal(sub(r'[^\d.]', '', rec['Amount'])) * multiplier
    return str(return_amount)


def trace(msg_str, trace_flag, banner=False):
    if trace_flag:
        if banner:
            print
            print '*************************************************************************************************' \
                '**********************'
            print '*** ' + msg_str
        else:
            print msg_str
        if banner:
            print '*************************************************************************************************' \
                '**********************'
            print


if __name__ == "__main__":
    main(sys.argv[1:])
