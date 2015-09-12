#!/usr/bin/env python


import sys, os.path, argparse, petl


def main(argv):

    global g

    parser = argparse.ArgumentParser()
    parser.add_argument("--contributions-filename", required=True, help="Input UTF8 CSV with contributions data "
        "dumped from Servant Keeper")
    parser.add_argument("--output-filename", required=True, help="Output CSV filename which will be loaded with "
        "contributions data in CCB import format ")
    parser.add_argument('--trace', action='store_true', help="If specified, prints tracing/progress messages to "
        "stdout")
    args = parser.parse_args()

    assert os.path.isfile(args.contributions_filename), "Error: cannot open file '" + args.contributions_filename + "'"

    table = petl.fromcsv(args.contributions_filename)

    table = petl.addfield(table, 'individual_id', lambda rec: rec['Individual ID'])
    table = petl.addfield(table, 'date of contribution', lambda rec: rec['Batch Date'])
    table = petl.addfield(table, 'amount', lambda rec: rec['Amount'])
    table = petl.addfield(table, 'type of gift', lambda rec: rec['Type'])
    table = petl.addfield(table, 'check number', lambda rec: rec['Check #'])
    table = petl.addfield(table, 'fund given to', lambda rec: rec['Account'])
    table = petl.addfield(table, 'sub fund', '')
    table = petl.addfield(table, 'campus associated with', 'Ingomar Church')
    table = petl.addfield(table, 'transaction_grouping', '')
    table = petl.addfield(table, 'batch number/name', '')
    table = petl.addfield(table, 'tax_deductible', lambda rec: rec['Tax'])
    table = petl.addfield(table, 'memo', lambda rec: rec['Notes'])

    trace('CONVERTING AND THEN EMITTING TO CSV FILE...', args.trace, banner=True)

    table.progress(200).tocsv(args.output_filename)

    trace('OUTPUT TO CSV COMPLETE.', args.trace, banner=True)

    trace('DONE!', args.trace, banner=True)


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
