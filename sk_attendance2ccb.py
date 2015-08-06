#!/usr/bin/env python

# Todos:
# x Cross check totals at bottom with sum(weekX) and sum(total) columns (to make sure no rows/data missed)
#   NOTE!  Cross checks failed.  Seems Servant Keeper is buggy in reporting totals.  So they are emitted to
#   stderr as WARNING (not ERROR) when Servant Keeper and data totals do not line up.
# x Allow for long full_name^M<spaces>phone^L<6 spaces><data> as formatted double-split tri-line
# x Allow for input file directory to be specified (in place of input filenames) and process all .txt files in that
#   directory
# x Allow name2member_id mapping file to be specified and emit member_id along with name in output CSV
# x Calculate weekX dates (from month and year)
# x Allow for long names with ^M followed by rest of line (a form of line folding)
# x Allow for first/last names to have '-' character in them
# x Allow first names to have '(' and ')' characters in them, like "Margaret (Meg)"
# x Allow first names in all caps (like "Houser, MC")
# x Allow first names with '.' (like "Houser, Kermit J.")
# x Allow spaces in last name (like "Etap Omia, Charlize")
# x Pull off service time
# x March 2015 service doesn't match on Total line (match2)
# x 'total' field not summed in 2dict()
# - Refactor add_attendance() vs row2dict() approaches to negative-indexing version for both (add_attendance() flavor)
# - Clean up code around dict2 stuff and drop original dict stuff
# - Emit output CSV file

import sys, getopt, os.path, csv, argparse, petl, re, calendar, pprint, glob, datetime


def main(argv):
    global full_name2sk_indiv_id

    parser = argparse.ArgumentParser()
    parser.add_argument("--attendance-filename", required=True, nargs='+', action='append', \
        help="Attendance filename (input Servant Keeper attendance report file(s)...can be wildcard)")
    parser.add_argument("--mapping-filename", required=True, help="'Mapping' filename (CSV mapping file with " \
        "'last_name', 'first_name' and 'sk_ind_id' columns)")
    parser.add_argument("--output-filename", required=True, help="'Output' filename (output CSV file " \
        "containing resulting <event_id>, <date>, <attending_individual_id> data)")
    parser.add_argument('--emit-data-csvs', action='store_true', help="If specified, output a CSV file per input " \
        "attendance data text file")
    args = parser.parse_args()

    # Load up mapping matrix to map from Servant Keeper full_name's to Servant Keeper individual_id's
    full_name2sk_indiv_id = {}
    with open(args.mapping_filename, 'rb') as csvfile:
        csvreader = csv.reader(csvfile)
        for row in csvreader:
            full_name2sk_indiv_id[row[0] + ',' + row[1]] = row[2]
#    print full_name2sk_indiv_id

    attendance_table = join_tables(args.attendance_filename[0], args.emit_data_csvs)


def join_tables(filename_pattern_list, emit_data_csvs):
    curr_table = None
    filenames_list = []
    for filename_pattern in filename_pattern_list:
        for filename in glob.glob(filename_pattern):
            filenames_list.append(filename)

    for filename in sorted(set(filenames_list)):
        if not os.path.isfile(filename):
            print >> sys.stderr, "*** Error! Cannot open file '" + filename + "'"
        else:
            next_table = attendance_file2table(filename, emit_data_csvs)
#            print next_table
#            print

#            for row in next_table:
#                print row

#            if curr_table is not None:
#                curr_table = table_extend(curr_table, next_table)
#            else:
#                curr_table = next_table
#    return curr_table

    return None

def attendance_file2table(filename, emit_data_csvs):
    global full_name2sk_indiv_id

    print '*** Parsing file: ' + filename
    print

    attendance_dicts = []

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
    event_id_strings[1] = '09am'
    event_id_strings[2] = '10am'
    event_id_strings[3] = '11_15am'
    event_id_strings[4] = '08am'

    # Starting state...
    prior_line = None
    matched_month_year = None
    matched_service_time = None
    month = None
    year = None
    service_time = None
    line_number = 1
    total_row_dict = None
    event_id = None
    accumulated_row_totals_dict = {
        'week1': 0,
        'week2': 0,
        'week3': 0,
        'week4': 0,
        'week5': 0,
        'week6': 0,
        'total': 0
    }
    full_name = None
    phone = None
    num_processed_lines = 0

    for line in open(filename):

        # First pick off line at front of file indicating month and year that this attendance file is for...
        if not matched_month_year:
            matched_month_year = re.search('For the month of ([A-Z][a-z]+), ([0-9]{4})', line)
            if matched_month_year:
                month = string2monthnum(matched_month_year.group(1))
                year = string2yearnum(matched_month_year.group(2))
                if not(month and year):
                    print >> sys.stderr, '*** Filename: ' + filename + ', line number: ' + str(line_number)
                    print >> sys.stderr, '*** ERROR! Invalid month or year found'
                    print >> sys.stderr, line
                    print >> sys.stderr
                    sys.exit(1)
                first_day_in_month, num_days_in_month = calendar.monthrange(year, month)

                # Create list of 6 date objects, month_sundays, representing week1, week2, ... week6 Sunday dates
                # If a week has no Sunday, it is None
                day_countup = 1
                day_countup += (6 - first_day_in_month)
                month_sundays = []
                if first_day_in_month != 6:
                    month_sundays.append(None)
                while day_countup <= num_days_in_month:
                    month_sundays.append(datetime.date(year, month, day_countup))
                    day_countup += 7
                while len(month_sundays) < 6:
                    month_sundays.append(None)

        # Second pick off line at front of file indicating worship service time that this attendance file is for...
        elif not matched_service_time:
            matched_service_time = re.search('Worship Service - (Sunday |Summer )([^ ]*)', line)
            if matched_service_time:
                service_time = matched_service_time.group(2)
                if service_time in event_ids:
                    event_id = event_ids[service_time]
                else:
                    print >> sys.stderr, '*** Filename: ' + filename + ', line number: ' + str(line_number)
                    print >> sys.stderr, '*** ERROR! Unrecognized service_time: "' + service_time + '"'
                    print >> sys.stderr
                    sys.exit(1)

        # ...then match attendance (row per person with weeks they attended) and total (summary at bottom) rows
        else:

            # Once we found row with totals...we're done, that's last line in attendance file we need to parse
#            matched_total_line = re.search('^ +Total: +([0-9]+ +)+[0-9]+\r?$', line)
#            if matched_total_line:
#                total_row_dict = row2dict(line, total_row_fields, None)
            matched_total_line2 = re.search('^ {18}Total: {13}(?P<attendance>( +[0-9]+)+)\r?$', line)
            if matched_total_line2:
                totals_attendance_dict = attendance_str2dict(matched_total_line2.group('attendance'),
                                                             [-3, -9, -15, -20, -24, -29, -35], 3)
#                print totals_attendance_dict
                break

            matched_attendance_line = re.search('^ {6}' \
                + '(?P<full_name>(?P<last_name>[A-Za-z]+([ \-\'][A-Za-z]+)*), ' \
                    +  '(?P<first_name>[A-Za-z]+([\-\' ][A-Za-z]+)*)( \((?P<nick_name>[A-Za-z]+)\))?\.?)?\r?'
                + '(?P<phone> +([0-9]{3}-[0-9]{3}-[0-9]{4}|Unlisted))?' \
                + '(?P<attendance> +(1 +)+[1-6])?\r?$', line)
            if matched_attendance_line:
                if matched_attendance_line.group('full_name'):
                    full_name = matched_attendance_line.group('full_name').strip()
                if matched_attendance_line.group('phone'):
                    phone = matched_attendance_line.group('phone').strip()
                if matched_attendance_line.group('attendance'):
                    if full_name:
                        attendance = matched_attendance_line.group('attendance').strip()
                        row_dict = attendance_str2dict(attendance, [-1, -7, -13, -18, -22, -27, -33], 1)
                        row_dict['full_name'] = full_name
                        if phone:
                            row_dict['phone'] = phone
                        else:
                            row_dict['phone'] = ''
#                        print '"' + attendance + '"'
#                        print attendance_str2dict(attendance, [-1, -7, -13, -18, -22, -27, -33], 1)
#                        print
#                        add_attendance(row_dict, attendance)
                        num_processed_lines += 1
                        full_name = None
                        phone = None
                        if row_dict['total'] != ( row_dict['week1'] + row_dict['week2'] + row_dict['week3'] +\
                            row_dict['week4'] + row_dict['week5'] + row_dict['week6']):
                            print >> sys.stderr, '*** Filename: ' + filename + ', line number: ' + str(line_number)
                            print >> sys.stderr, '*** ERROR! Bad row total, doesn\'t match sum of weeks 1-6'
                            print >> sys.stderr, row_dict
                            print >> sys.stderr
                            break

                        for key in accumulated_row_totals_dict:
                            accumulated_row_totals_dict[key] += row_dict[key]
                        attendance_dicts.append(row_dict)

            # Buffer the current line for line folding if needed (see 'line folding' above)
            prior_line = line
            line_number += 1

    print '*** Number of processed attendance lines in file: ' + str(num_processed_lines)
    print

    return_table = petl.fromdicts(attendance_dicts)

    if emit_data_csvs and event_id:
        output_csv_filename = os.path.dirname(filename) + '/' + str(year) + format(month, '02d') + '_' + \
                              str(event_id_strings[event_id]) + '.csv'
        petl.tocsv(return_table, output_csv_filename)

    attendance_dicts2 = []
    for attendance_dict in attendance_dicts:
        for key in attendance_dict:
            if key[:4] == 'week':
                week_index = int(key[4:5]) - 1
                if month_sundays[week_index] is not None:
                    matched_last_first = re.search('(?P<last_name>[A-Za-z]+([ \-\'][A-Za-z]+)*), ' \
                        '(?P<first_name>[A-Za-z]+([\-\' ][A-Za-z]+)*)', attendance_dict['full_name'])
                    if matched_last_first:
                        attendance_dict2 = {}
                        full_name = attendance_dict['full_name'].replace(', ', ',')
                        if full_name in full_name2sk_indiv_id:
                            attendance_dict2['sk_indiv_id'] = full_name2sk_indiv_id[full_name]
                            attendance_dict2['date'] = month_sundays[week_index]
                            attendance_dict2['event_id'] = event_id
#                            print attendance_dict2
                            attendance_dicts2.append(attendance_dict2)
                        else:
                            print >> sys.stderr, '*** WARNING! Cannot find "' + full_name + '" in map'

    # Check if numbers on Servant Keeper's reported Total: line match the totals we've been accumulating
    # per attendance row entry.  If they don't match, show WARNING (not ERROR, since via manual checks, it appears
    # that Servant Keeper totals are buggy)
    if totals_attendance_dict:
        for key in accumulated_row_totals_dict:
            if accumulated_row_totals_dict[key] != totals_attendance_dict[key]:
                pp = pprint.PrettyPrinter(stream=sys.stderr)
                print >> sys.stderr, '*** WARNING! Servant Keeper reported totals do not match data totals'
                print >> sys.stderr, 'Servant Keeper Totals:'
                pp.pprint(totals_attendance_dict)
                print >> sys.stderr, 'Data Totals:'
                pp.pprint(accumulated_row_totals_dict)
                print >> sys.stderr
                break

    return return_table


def add_attendance(dict, attendance_str):

    dict['total'] = int(attendance_str[-1])

    week_offsets = [-7, -13, -18, -22, -27, -33]

    for index, offset in enumerate(week_offsets):
        if abs(offset) < (len(attendance_str) + 1) and attendance_str[offset] == '1':
            dict['week' + str(6 - index)] = 1
        else:
            dict['week' + str(6 - index)] = 0

            
def attendance_str2dict(attendance_str, offsets_list, field_len):
    """
    Parses numeric fields at negative-offset positions in string

    :param str attendance_str: The string containing integer numeric fields named 'week1', 'week2', ... 'week6',
    'total' from left to right

    :param list offsets_list: A list of 7 negative offsets starting with right-most ('total'), then 'week6' ... 'week1'
    field offset positions all expressed as negative integer (specifying distance from end of string to the first
    character in the field

    :param int field_len: Fixed length of all fields being parsed from the string.  If numbers range from 0-999, then
    would be 3.  If numbers range from 0-9, then would be 1

    :return: Dictionary of integer field values for 'week1'...'week6' and 'total'
    :rtype: dict
    """
#    print '"' + attendance_str + '"'
    return_dict = {}
    spaces = ' ' * field_len
    for index, offset in enumerate(offsets_list):
        if index == 0:
            field_name = 'total'
        else:
            field_name = 'week' + str(7 - index)
        if abs(offset) < (len(attendance_str) + 1):
            if offset+field_len == 0:
                field_str = attendance_str[offset:].strip()
            else:
                field_str = attendance_str[offset:offset+field_len].strip()
            if field_str == '':
                field_value = 0
            else:
                field_value = int(field_str)
        else:
            field_value = 0
#            field_str = ''
#        print index, offset, field_len, '"' + field_str + '"', field_name, field_value
        return_dict[field_name] = field_value
    return return_dict


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
