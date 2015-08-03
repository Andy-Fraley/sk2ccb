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

import sys, getopt, os.path, csv, argparse, petl, re, calendar, pprint

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
#            for row in next_table:
#                print row

#            if curr_table is not None:
#                curr_table = table_extend(curr_table, next_table)
#            else:
#                curr_table = next_table
#    return curr_table

    return None

def attendance_file2table(filename):

    attendance_dicts = []

    attendance_row_fields = {
        'full_name': { 'start': 6, 'end': 25, 'type': 'string' },
        'phone': { 'start': 27, 'end': 38, 'type': 'string' },
        'week1': { 'start': 40, 'end': 40, 'type': 'number' },
        'week2': { 'start': 46, 'end': 46, 'type': 'number' },
        'week3': { 'start': 51, 'end': 51, 'type': 'number' },
        'week4': { 'start': 55, 'end': 55, 'type': 'number' },
        'week5': { 'start': 60, 'end': 60, 'type': 'number' },
        'week6': { 'start': 66, 'end': 66, 'type': 'number' },
        'total': { 'start': 72, 'end': 72, 'type': 'number' }
    }

    total_row_fields = {
        'week1': { 'start': 38, 'end': 40, 'type': 'number' },
        'week2': { 'start': 44, 'end': 46, 'type': 'number' },
        'week3': { 'start': 49, 'end': 51, 'type': 'number' },
        'week4': { 'start': 53, 'end': 55, 'type': 'number' },
        'week5': { 'start': 58, 'end': 60, 'type': 'number' },
        'week6': { 'start': 64, 'end': 66, 'type': 'number' },
        'total': { 'start': 70, 'end': 72, 'type': 'number' }
    }

    # Service event IDs...plug these with actuals out of CCB once worship service events created
    event_ids = {}
    event_ids['9'] = 1
    event_ids['10'] = 2
    event_ids['11:15'] = 3
    event_ids['8'] = 4

    # The following are only needed for reverse mapping to create CSV filenames.
    # TODO - delete these settings...not needed by core program
    event_id_strings = {}
    event_id_strings[1] = '9am'
    event_id_strings[2] = '10am'
    event_id_strings[3] = '11_15am'
    event_id_strings[4] = '8am'

    # Starting state...found nothing
    prior_line = None
    matched_month_year = None
    matched_service_time = None
    month = None
    year = None
    service_time = None
    num_matched_name_lines = 0

    accumulated_row_totals_dict = {
        'week1': 0,
        'week2': 0,
        'week3': 0,
        'week4': 0,
        'week5': 0,
        'week6': 0,
        'total': 0
    }

    for line in open(filename):

        # First pick off line at front of file indicating month and year that this attendance file is for...
        if not matched_month_year:
            matched_month_year = re.search('For the month of ([A-Z][a-z]+), ([0-9]{4})', line)
            if matched_month_year:
                month = string2monthnum(matched_month_year.group(1))
                year = string2yearnum(matched_month_year.group(2))
                if not(month and year):
                    print >> sys.stderr, 'Invalid month or year found'
                    print >> sys.stderr, line
                    sys.exit(1)

        # Second pick off line at front of file indicating worship service time that this attendance file is for...
        elif not matched_service_time:
            matched_service_time = re.search('Worship Service - Sunday ([^ ]*)', line)
            if matched_service_time:
                service_time = matched_service_time.group(1)
                if service_time in event_ids:
                    event_id = event_ids[service_time]
                else:
                    print >> sys.stderr, '*** ERROR! Unrecognized service_time: "' + service_time + '"'
                    sys.exit(1)

        # ...then match attendance (row per person with weeks they attended) and total (summary at bottom) rows
        else:

            matched_name_line = re.search('^\s*([A-Za-z\-\'\s]+[A-Za-z],\s+' \
                + '[A-Za-z\-\'\s]+[A-Za-z](\s\([A-Za-z]+\))?\.?)', line)
            if matched_name_line:
                print line
                num_matched_name_lines += 1

            # Once we found row with totals...we're done, that's last line in attendance file we need to parse
            matched_total_line = re.search('^ +Total: +([0-9]+ +)+[0-9]+\r?$', line)
            if matched_total_line:
                total_row_dict = row2dict(line, total_row_fields, None)
                break

            # Because of weird line wraps in attendance files, we may need to fold a line with a prior line
            # (prior_line), and need to track if we've match a complete line or just a fragment or non data line
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
                        line = ' ' * (attendance_row_fields['full_name']['end'] + 2) + matched_complete_line.group(3)
                    else:
                        alt_full_name = None

            if found_complete_line:

                # Convert line to row dictionary
                if alt_full_name is not None:
                    alt_fields = { 'full_name': alt_full_name }
                else:
                    alt_fields = None
                alt_full_name = None
                row_dict = row2dict(line, attendance_row_fields, alt_fields)
                if row_dict['total'] != ( row_dict['week1'] + row_dict['week2'] + row_dict['week3'] +\
                                          row_dict['week4'] + row_dict['week5'] + row_dict['week6']):
                    print >> sys.stderr, 'ERROR:  Bad row total, doesn\'t match sum of weeks 1-6:'
                    print >> sys.stderr, row_dict
                    sys.exit(1)
                for key in accumulated_row_totals_dict:
                    accumulated_row_totals_dict[key] += row_dict[key]
                attendance_dicts.append(row_dict)

            # Buffer the current line for line folding if needed (see 'line folding' above)
            prior_line = line

    return_table = petl.fromdicts(attendance_dicts)

    output_csv_filename = os.path.abspath( os.path.dirname(filename) + '/' + str(year) + format(month, '02d') + '_' + \
        str(event_id_strings[event_id]) + '.csv' )
    print output_csv_filename
    petl.tocsv(return_table, output_csv_filename)

    print '*** Num matched name lines: ' + str(num_matched_name_lines)

    for key in accumulated_row_totals_dict:
        if accumulated_row_totals_dict[key] != total_row_dict[key]:
            pp = pprint.PrettyPrinter(stream=sys.stderr)
            print >> sys.stderr, '*** WARNING:  Servant Keeper reported totals do not match data totals!'
            print >> sys.stderr, 'Servant Keeper Totals:'
            pp.pprint(total_row_dict)
            print >> sys.stderr, 'Data Totals:'
            pp.pprint(accumulated_row_totals_dict)
            break

    return petl.fromdicts(attendance_dicts)

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

def row2dict(row, fields, alt_fields):
    dict = {}

    # Pull lines from fixed length fields in row
    for field in fields:

        # If there's an alt_field provided, use it
        if alt_fields is not None and field in alt_fields:
            dict[field] = alt_fields[field]
        # Else, parse field out of fixed-length substring within the row
        else:
            field_str = row[fields[field]['start']:fields[field]['end']+1].strip()
            if fields[field]['type'] == 'number':
                if len(field_str) > 0:
                    field_value = int(field_str)
                else:
                    field_value = 0
            else:
                field_value = field_str
            dict[field] = field_value

    return dict

if __name__ == "__main__":
    main(sys.argv[1:])
