#!/usr/bin/env python


import sys, os.path, argparse, petl


# Fake class only for purpose of limiting global namespace to the 'g' object
class g:
    set_unfound_accounts = set()


def main(argv):

    global g

    parser = argparse.ArgumentParser()
    parser.add_argument("--contributions-filename", required=True, help="Input UTF8 CSV with contributions data "
        "dumped from Servant Keeper")
    parser.add_argument("--chart-of-accounts-filename", required=True, help="Input UTF8 CSV with Chart of Accounts "
        "data from Servant Keeper")
    parser.add_argument("--output-filename", required=True, help="Output CSV filename which will be loaded with "
        "contributions data in CCB import format ")
    parser.add_argument('--trace', action='store_true', help="If specified, prints tracing/progress messages to "
        "stdout")
    args = parser.parse_args()

    assert os.path.isfile(args.contributions_filename), "Error: cannot open file '" + args.contributions_filename + "'"

    table = petl.fromcsv(args.contributions_filename)
    table = petl.rename(table, {
        'Individual ID': 'SK Individual ID',
        'Amount': 'SK Amount'
        })
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


if __name__ == "__main__":
    main(sys.argv[1:])
