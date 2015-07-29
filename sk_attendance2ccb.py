#!/usr/bin/env python

import sys, getopt, os.path, csv, argparse, petl, re, calendar

def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument("--attendance-filename", required=True, nargs='+', action='append', \
        help="Attendance filename (input Servant Keeper attendance report file)")
    parser.add_argument("--output-filename", required=True, help="'Output' filename (output XLS file)")
    args = parser.parse_args()

    attendance_table = join_tables(args.attendance_filename[0])

def join_tables(filename_list):
    curr_table = None
    for filename in filename_list:
        if not os.path.isfile(filename):
            print "Error: cannot open file '" + filename + "'"
        else:
            next_table = attendance_file2table(filename)
            if curr_table is not None:
                curr_table = table_extend(curr_table, next_table)
            else:
                curr_table = next_table
    return curr_table

def attendance_file2table(filename):

    prior_line = None

    # Length 75 = normal full-length line including full_name, phone, week1-6, total
    # Length 41 = line truncated after numeric 'xxx-xxx-xxxx' phone (number)
    # Length 37 = line truncated after 'Unlisted' phone (number)
    # Length 12-28 = line truncated after full_name (pattern = '^ {6}[A-Za-z]+, [A-Za-z' ]+\r?$')

    # Field locations within string
    fields = {}
    fields['full_name'] = [6,25]
    fields['phone'] = [27,38]
    fields['week1'] = [40,40]
    fields['week2'] = [46,46]
    fields['week3'] = [51,51]
    fields['week4'] = [55,55]
    fields['week5'] = [60,60]
    fields['week6'] = [66,66]
    fields['total'] = [72,72]

    regex_partial_line_thru_phone_numeric = re.compile('^ {6}[A-Za-z\']+, [A-Za-z\' ]+[a-z] +[0-9]{3}-[0-9]{3}-[0-9]{4}\r?$')
    regex_partial_line_thru_phone_unlisted = re.compile('^ {6}[A-Za-z\']+, [A-Za-z\' ]+[a-z] +Unlisted\r?$')
    regex_partial_line_thru_full_name = re.compile('^ {6}[A-Za-z\']+, [A-Za-z\' ]+[a-z]\r?$')
    regex_complete_line = re.compile('^ {6}[A-Za-z\']+, [A-Za-z\' ]+[a-z] +([0-9]{3}-[0-9]{3}-[0-9]{4}|Unlisted)? +(1 +)+[1-6]\r?$')
    regex_month_year = re.compile('For the month of ([A-Z][a-z]+), ([0-9]{4})')
    regex_attendance_only = re.compile('^ +(1).*([1-6])\r?$')
#    regex_name_phone_newline = re.compile(' +([A-Za-z\']+), ([A-Za-z]+( [A-Za-z]+)?) +( {12}|[0-9]{3}-[0-9]{3}-[0-9]{4})$')
    regex_name_phone_newline = re.compile('^ +([A-Za-z\']+), ([A-Za-z]+( [A-Za-z]+)?)( +(Unlisted|[0-9]{3}-[0-9]{3}-[0-9]{4}))?\r?$')
    for line in open(filename):

        # If line only contains attendance info (no full name, phone/Unlisted, etc.), then blend it with prior line
        matched_attendance_only_line = re.search('^ +((1 +)+[1-6])\r?$', line)
        if matched_attendance_only_line and prior_line:
            print
            print '*** FOLDED LINE'
            print len(prior_line)
            print len(line)
            print '   *** PRIOR LINE'
            print prior_line
            print '   *** LINE BEFORE PROCESSING'
            print line
            line = ' ' * 6 + prior_line.strip() + ' ' * (matched_attendance_only_line.start(1) - len(prior_line) + 2) + matched_attendance_only_line.group(1)
            print '   *** FOLDED LINE AFTER PROCESSING'
            print line
            print

        attendance_only = regex_attendance_only.search(line)
        if attendance_only != None:
            print line

        print 'length: ' + str(len(line))

        match_partial_line_thru_phone_numeric = regex_partial_line_thru_phone_numeric.search(line)
        match_partial_line_thru_phone_unlisted = regex_partial_line_thru_phone_unlisted.search(line)
        match_partial_line_thru_full_name = regex_partial_line_thru_full_name.search(line)
        match_complete_line = regex_complete_line.search(line)
        if match_partial_line_thru_phone_numeric != None:
            print '*** MATCHED!  PARTIAL LINE THRU PHONE NUMERIC'
        elif match_partial_line_thru_phone_unlisted != None:
            print '*** MATCHED!  PARTIAL LINE THRU PHONE UNLISTED'
        elif match_partial_line_thru_full_name != None:
            print '*** MATCHED!  PARTIAL LINE THRU FULL NAME'
        elif match_complete_line != None:
            print '*** MATCHED!  COMPLETE LINE'

        for field in fields:
            print field, '"' + line[fields[field][0]:fields[field][1]+1].strip() + '"'
        month_year = regex_month_year.search(line)
        if month_year != None:
            month = string2monthnum(month_year.group(1))
            year = string2yearnum(month_year.group(2))
            if month and year:
                print year, month
        name_phone_newline = regex_name_phone_newline.search(line)
        if name_phone_newline != None:
            print line
        attendance_only = regex_attendance_only.search(line)
        if attendance_only != None:
            print line

        prior_line = line

    return None

def string2monthnum(str):
    try:
        return list(calendar.month_name)[1:].index(str)+1
    except ValueError:
        return None

def string2yearnum(str):
    try:
        return int(str)
    except ValueError:
        return None

if __name__ == "__main__":
    main(sys.argv[1:])
