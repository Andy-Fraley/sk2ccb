#!/usr/bin/env python

# Todos:
# - Cross check totals at bottom with sum(weekX) and sum(total) columns (to make sure no rows/data missed)
# - Allow for input file directory to be specified (in place of input filenames) and process all .txt files in that
#   directory
# - Allow name2member_id mapping file to be specified and emit member_id along with name in output CSV
# - Calculate weekX dates (from month and year)
# x Allow for long names with ^M followed by rest of line (a form of line folding)
# x Allow for first/last names to have '-' character in them
# x Allow first names to have '(' and ')' characters in them, like "Margaret (Meg)"
# x Allow first names in all caps (like "Houser, MC")
# x Allow first names with '.' (like "Houser, Kermit J.")
# x Allow spaces in last name (like "Etap Omia, Charlize")
# x Pull off service time

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

    # Service event IDs
    event_ids = {}
    event_ids['8'] = 4
    event_ids['9'] = 1
    event_ids['10'] = 2
    event_ids['11:15'] = 3

    prior_line = None
    matched_month_year = None
    matched_service_time = None
    month = None
    year = None
    service_time = None
    alt_full_name = None

    attendance_line_sums = {}
    found_names = []

    for line in open(filename):

#        print line
#        print

        # Don't try finding data lines until we picked up line indicating Month/Year towards beginning of file
        if not matched_month_year:
            matched_month_year = re.search('For the month of ([A-Z][a-z]+), ([0-9]{4})', line)
            if matched_month_year:
                month = string2monthnum(matched_month_year.group(1))
                year = string2yearnum(matched_month_year.group(2))
                if month and year:
                    print '*** year = ' + str(year) + ', month = ' + str(month)
                else:
                    print >> sys.stderr, 'Invalid month or year found'
                    print >> sys.stderr, line
                    sys.exit(1)

        elif not matched_service_time:
            matched_service_time = re.search('Worship Service - Sunday ([^ ]*)', line)
            if matched_service_time:
                service_time = matched_service_time.group(1)
                if service_time in event_ids:
                    event_id = event_ids[service_time]
                    print '*** service_time = ' + service_time + ' a.m., event_id = ' + str(event_id)
                else:
                    print '*** ERROR! Unrecognized service_time: "' + service_time + '"'

        # Match and process lines containing data
        else:

#                  Total:                    133  134 145  109         521
#                  Total:               85   111   99 129  142         566
#                  Total:                    118  119 140  104   111   592
            total_offsets = {}
            total_offsets['week1'] = 38
            total_offsets['week2'] = 44
            total_offsets['week3'] = 49
            total_offsets['week4'] = 53
            total_offsets['week5'] = 58
            total_offsets['week6'] = 64
            total_offsets['total'] = 70
            total_line_values = {}
            matched_total_line = re.search('^ +Total: +([0-9]+ +)+[0-9]+\r?$', line)
            if matched_total_line:
                for total_offset_name in total_offsets:
                    offset = total_offsets[total_offset_name]
                    total_str = line[offset:offset+3].strip()
                    if len(total_str) > 0:
                        total = int(total_str)
                    else:
                        total = 0
                    total_line_values[total_offset_name] = total
                print '*** Total line:'
                print line
                print total_line_values
                print attendance_line_sums
                for found_name in found_names:
                    print found_name
                print

            found_complete_line = False

            # One form of data line contains only attendance data for weeks 1-6 and total.  If we find one of
            # these, take prior line (which contains name and maybe phone) and fold them together to create a
            # whole data line (prior_line is stashed on earlier pass just in case this line folding is needed)
            matched_attendance_only_line = re.search('^ +((1 +)+[1-6])\r?$', line)
            if matched_attendance_only_line and prior_line:
                line = ' ' * 6 + prior_line.strip() + ' ' * (matched_attendance_only_line.start(1) - \
                    len(prior_line) + 2) + matched_attendance_only_line.group(1)
                found_complete_line = True

            else:
                # Another form of data line is a complete line with full_name, phone (optional), followed
                # by attendance data for weeks 1-6 and total
                matched_complete_line = re.search('^ {6}([A-Za-z\-\' ]+[A-Za-z], ' \
                    + '[A-Za-z\-\' ]+[A-Za-z]( \([A-Za-z]+\))?\.?)\r? +' '(([0-9]{3}-[0-9]{3}-[0-9]{4}|Unlisted)? +' \
                    + '(1 +)+[1-6])\r?$', line)
                if matched_complete_line:

                    for match in matched_complete_line.groups():
                        print '*** Match: ' + str(match)

                    found_complete_line = True

                    # In one form of complete line, if the name is too big to fit into the full_name field,
                    # it is followed by carriage return (not newline) and the next line contains the phone (if
                    # present) and attandance data.  If this pattern occurs, we have to stash the (too long)
                    # full name (it's set aside in alt_full_name), reformat the line without full_name (since it
                    # doesn't fit), and then pull all fields except full_name normally and use alt_full_name
                    # instead of truncated version of full_name that would be pulled from fixed-length full_name
                    # field
                    if len(matched_complete_line.group(1)) > 19:
                        alt_full_name = matched_complete_line.group(1)
                        line = ' ' * (fields['full_name'][1] + 2) + matched_complete_line.group(3)
                        print
                        print 'Alt name line:'
                        print line
                        print
                    else:
                        alt_full_name = None

            if found_complete_line:
                # Pull lines from fixed length fields in 'line'
                for field in fields:

                    # Use alt_full_name instead of fixed-length full_name field if it was set aside above
                    if field == 'full_name' and alt_full_name is not None:
                        print field, '"' + alt_full_name + '"'
                        found_names.append(alt_full_name)
                        alt_full_name = None
                    else:
                        start = fields[field][0]
                        end = fields[field][1]+1
                        field_str = line[start:end].strip()
                        if field[:4] == 'week' or field == 'total':
                            if len(field_str) > 0:
                                field_value = int(field_str)
                            else:
                                field_value = 0
                            if field in attendance_line_sums:
                                attendance_line_sums[field] += field_value
                            else:
                                attendance_line_sums[field] = field_value
                        elif field == 'full_name':
                            found_names.append(field_str)
                        print field, '"' + field_str + '"'
                print

            # Buffer the current line for line folding if needed (see 'line folding' above)
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
