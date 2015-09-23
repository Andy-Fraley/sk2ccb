#!/usr/bin/env python


import sys, os.path, argparse, petl
import re
from decimal import Decimal


# Fake class only for purpose of limiting global namespace to the 'g' object
class g:
    set_unfound_accounts = set()


def main(argv):

    global g

    parser = argparse.ArgumentParser()
    parser.add_argument("--contributions-filename", required=True, help="Input UTF8 CSV with contributions data "
        "dumped from Servant Keeper")
    parser.add_argument("--split-detail-files", required=False, nargs='*', default=argparse.SUPPRESS,
        help="List of CSV files which have records that can be used to replace top-level 'Split Transaction' "
        "records in the main contributions file.")
    parser.add_argument("--chart-of-accounts-filename", required=True, help="Input UTF8 CSV with Chart of Accounts "
        "data from Servant Keeper")
    parser.add_argument("--output-filename", required=True, help="Output CSV filename which will be loaded with "
        "contributions data in CCB import format ")
    parser.add_argument('--trace', action='store_true', help="If specified, prints tracing/progress messages to "
        "stdout")
    args = parser.parse_args()

    assert os.path.isfile(args.contributions_filename), "Error: cannot open file '" + args.contributions_filename + "'"

    dict_split_transaction_details = load_split_transaction_details(args.split_detail_files)

    table = petl.fromcsv(args.contributions_filename)
    table = petl.rename(table, {
        'Individual ID': 'SK Individual ID',
        'Amount': 'SK Amount'
        })
    table = replace_split_transactions(table, dict_split_transaction_details)

    sys.exit(1)

    table_coa = petl.fromcsv(args.chart_of_accounts_filename)
    table = petl.leftjoin(table, table_coa, lkey='Account', rkey='SK Account')

    table = petl.addfield(table, 'Individual ID', lambda rec: rec['SK Individual ID'])
    table = petl.addfield(table, 'Date of Contribution', lambda rec: rec['Batch Date'])
    table = petl.addfield(table, 'Amount', lambda rec: rec['SK Amount'])
    table = petl.addfield(table, 'Type of Gift', lambda rec: rec['Type'])
    table = petl.addfield(table, 'Check Number', lambda rec: rec['Check #'])
    table = petl.addfield(table, 'Fund', convert_fund)
    table = petl.addfield(table, 'Sub Fund', convert_sub_fund)
    table = petl.addfield(table, 'Campus', '')
    table = petl.addfield(table, 'Transaction Grouping', '')
    table = petl.addfield(table, 'Batch Number/Name', '')
    table = petl.addfield(table, 'Tax Deductible', lambda rec: rec['Tax'])
    table = petl.addfield(table, 'Memo', convert_notes)

    trace('CONVERTING AND THEN EMITTING TO CSV FILE...', args.trace, banner=True)

    table.progress(200).tocsv(args.output_filename)

    trace('OUTPUT TO CSV COMPLETE.', args.trace, banner=True)

    if len(g.set_unfound_accounts) > 0:
        trace('UNMATCHED SK ACCOUNTS!', args.trace, banner=True)
        for acct in g.set_unfound_accounts:
            trace(acct, args.trace)

    trace('DONE!', args.trace, banner=True)


def convert_fund(rec):
    if not rec['CCB Fund']:
        g.set_unfound_accounts.add(rec['Account'])
        return ''
    else:
        return rec['CCB Fund']


def convert_sub_fund(rec):
    if rec['CCB Fund'] == '':
        return ''
    else:
        return rec['CCB Sub Fund']


def convert_notes(rec):
    return_note = ''
    if rec['Note']:
        return_note = rec['Note']
    if rec['Notes']:
        if return_note:
            return_note += '. '
        return_note += rec['Notes']
    return return_note


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

def load_split_transaction_details(list_split_details_files):
    dict_split_transaction_details = {}
    if list_split_details_files is not None:
        for split_details_file in list_split_details_files:
            assert os.path.isfile(split_details_file), "Error: cannot open file '" + split_details_file + "'"
            table = petl.fromcsv(split_details_file)
            account_name = get_account_name(petl.values(table, 'Account'))
            for row in petl.records(table):
                if row['Account'] == 'Split Transaction':
                    string_key = row['Individual ID'] + ',' + row['Batch Date']
                    if string_key not in dict_split_transaction_details:
                        dict_split_transaction_details[string_key] = []
                    dict_split_transaction_details[string_key].append({
                        'Account': account_name,
                        'Amount': row['Amount'],
                        'Tax': row['Tax']
                        })
    return dict_split_transaction_details


def get_account_name(list_values):
    unique_values = set()
    for value in list_values:
        unique_values.add(value)
    if len(unique_values) > 2:
        return None
    elif not 'Split Transaction' in unique_values:
        return None
    else:
        for unique_value in unique_values:
            if unique_value != 'Split Transaction':
                return unique_value
        return None


def replace_split_transactions(table, dict_split_transaction_details):
    for row in petl.records(table):
        if row['Account'] == 'Split Transaction':
            string_key = row['SK Individual ID'] + ',' + row['Batch Date']
            contrib_amount = Decimal(re.sub(r'[^\d.]', '', row['SK Amount']))
            if string_key in dict_split_transaction_details:
                splits_total = Decimal(0)
                for split_entry in dict_split_transaction_details[string_key]:
                    splits_total += Decimal(re.sub(r'[^\d.]', '', split_entry['Amount']))
                if contrib_amount != splits_total:
                    print "*** ERROR!  For Individual ID, Batch Date " + string_key + ", the main 'Split " \
                        "Transaction' entry amount was " + str(contrib_amount) + "but sum of split detail " \
                        "transactions was " + str(splits_total)
            else:
                print "*** ERROR!  Cannot find any 'Split Transaction' details for record with 'Batch Date' " + \
                    row['Batch Date'] + ", contributed by 'Individual ID' " + row['SK Individual ID'] + " for the " \
                    "amount " + row['SK Amount']


if __name__ == "__main__":
    main(sys.argv[1:])
