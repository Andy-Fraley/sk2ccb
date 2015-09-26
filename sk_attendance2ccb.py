#!/usr/bin/env python


import sys, getopt, os.path, csv, argparse, petl, re, calendar, pprint, glob, datetime


def main(argv):
    global full_name2sk_indiv_id

    parser = argparse.ArgumentParser()
    parser.add_argument("--attendance-filename", required=True, nargs='+', action='append', \
        help="Attendance filename (input Servant Keeper attendance report file(s)...can be wildcard)")
    parser.add_argument("--mapping-filename", required=True, help="'Mapping' filename (CSV mapping file with " \
        "'Last Name', 'Preferred Name' and 'Individual ID' Servant Keeper data columns)")
    parser.add_argument("--output-filename", required=True, help="'Output' filename (output loading CSV file " \
                        "containing resulting <date>, <time>, <ccb_event_id>, <sk_indiv_id> data)")
    parser.add_argument('--emit-data-csvs', action='store_true', help="If specified, output a CSV file per input " \
        "attendance data text file")
    parser.add_argument('--add-extra-fields', action='store_true', help="If specified, emit attender's full name, " \
                        "event name, and Servant Keeper week number in addition to base fields into loading CSV file")
    args = parser.parse_args()

    # Load up mapping matrix to map from Servant Keeper full_name's to Servant Keeper individual_id's
    full_name2sk_indiv_id = {}
    with open(args.mapping_filename, 'rb') as csvfile:
        csvreader = csv.reader(csvfile)
        for row in csvreader:
            full_name2sk_indiv_id[row[0] + ', ' + row[1]] = row[2]

    if args.emit_data_csvs:
        output_csv_filebase = os.path.dirname(args.output_filename)
    else:
        output_csv_filebase = None

    attendance_table = join_tables(args.attendance_filename[0], output_csv_filebase, args.add_extra_fields)

    petl.tocsv(attendance_table, args.output_filename)


def join_tables(filename_pattern_list, output_csv_filebase, add_extra_fields):
    curr_table = None
    filenames_list = []
    for filename_pattern in filename_pattern_list:
        for filename in glob.glob(filename_pattern):
            filenames_list.append(filename)

    for filename in sorted(set(filenames_list)):
        if not os.path.isfile(filename):
            print >> sys.stderr, "*** Error! Cannot open file '" + filename + "'"
            print >> sys.stderr
        else:
            next_table = attendance_file2table(filename, output_csv_filebase, add_extra_fields)
            if curr_table is not None:
                curr_table = petl.cat(curr_table, next_table)
            else:
                curr_table = next_table

    return curr_table


def attendance_file2table(filename, output_csv_filebase, add_extra_fields):
    global full_name2sk_indiv_id

    print '*** Parsing file: ' + filename
    print

    attendance_dicts = []

    # CCB's Worship Service event IDs...
    event_ids = {}
    event_ids['8'] = 6
    event_ids['9'] = 7
    event_ids['10'] = 8
    event_ids['11:15'] = 9
    event_ids['Christmas'] = 13

    # The following are used to create CSV output filenames and to emit human-readable event name if add_extra_fields
    # flag is on
    event_names = {}
    event_names[6] = '08am'
    event_names[7] = '09am'
    event_names[8] = '10am'
    event_names[9] = '11_15am'
    event_names[13] = 'Christmas Eve'

    # Time of event in Excel-parseable format
    event_times = {}
    event_times[6] = '08:00 AM'
    event_times[7] = '09:00 AM'
    event_times[8] = '10:00 AM'
    event_times[9] = '11:15 AM'
    event_times[13] = '04:00 PM'

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
                christmas_eve_date = datetime.date(year, month, 24)

        # Second pick off line at front of file indicating worship service time that this attendance file is for...
        elif not matched_service_time:
            matched_service_time = re.search('Worship Service - (Sunday |Summer )?([^ ]*)', line)
            if matched_service_time:
                service_time = matched_service_time.group(2)
                if service_time in event_ids:
                    event_id = event_ids[service_time]
                    event_name = event_names[event_id]
                else:
                    print >> sys.stderr, '*** Filename: ' + filename + ', line number: ' + str(line_number)
                    print >> sys.stderr, '*** ERROR! Unrecognized service_time: "' + service_time + '"'
                    print >> sys.stderr
                    sys.exit(1)

        # ...then match attendance (row per person with weeks they attended) and total (summary at bottom) rows
        else:

            # Once we found row with totals...we're done, that's last line in attendance file we need to parse
            matched_total_line = re.search('^ {18}Total: {13}(?P<attendance>( +[0-9]+)+)\r?$', line)
            if matched_total_line:
                totals_attendance_dict = attendance_str2dict(matched_total_line.group('attendance'),
                                                             [-3, -9, -15, -20, -24, -29, -35], 3)
                break

            matched_attendance_line = re.search('^ {6}' \
                + '(?P<full_name>(?P<last_name>[A-Za-z]+([ \-\'][A-Za-z]+)*), ' \
                    +  '(?P<first_name>([A-Za-z]+\.?)+([\-\' ][A-Za-z]+)*)( \((?P<nick_name>[A-Za-z]+)\))?\.?)?\r?'
                + '(?P<phone>( +)?([0-9]{3}-[0-9]{3}-[0-9]{4}|Unlisted))?' \
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

    print '*** Number of attendance lines processed: ' + str(num_processed_lines)
    print '*** Number of attendees: ' + str(accumulated_row_totals_dict['total'])
    print

    if output_csv_filebase and event_id:
        output_csv_filename = output_csv_filebase + '/' + str(year) + format(month, '02d') + '_' + \
                              str(event_names[event_id]) + '.csv'
        all_columns_table = petl.fromdicts(attendance_dicts)
        petl.tocsv(all_columns_table, output_csv_filename)

    # Build 2nd list of dicts, where each list item is dict of individual date/event attendance.  I.e. a row per
    # worship service date vs original attendance dicts format of a row per attendee across all weeks in month.
    # This is the actual one returned and eventually emitted into output file
    attendance_dicts2 = []
    for attendance_dict in attendance_dicts:
        for key in attendance_dict:
            if key[:4] == 'week' and attendance_dict[key] != 0:
                week_index = int(key[4:5]) - 1
                if month_sundays[week_index] is not None:
                    attendance_dict2 = {}
                    full_name = attendance_dict['full_name']
                    if full_name in full_name2sk_indiv_id:
                        attendance_dict2['Individual ID'] = full_name2sk_indiv_id[full_name]
                        if event_name == 'Christmas Eve':
                            attendance_dict2['Date'] = christmas_eve_date
                        else:
                            attendance_dict2['Date'] = month_sundays[week_index]
                        attendance_dict2['Event ID'] = event_id
                        if add_extra_fields:
                            attendance_dict2['Time'] = event_times[event_id]
                            attendance_dict2['Full Name'] = full_name
                            attendance_dict2['Event Name'] = event_name
                            attendance_dict2['Week Num'] = week_index + 1
                        attendance_dicts2.append(attendance_dict2)
                    else:
                        print >> sys.stderr, '*** WARNING! Cannot find "' + full_name + '" in map'
                        print >> sys.stderr
                else:
                    print >> sys.stderr, '*** WARNING! Cannot find Sunday date for week index "' + \
                        str(week_index) + '"'
                    print >> sys.stderr

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

    return_table = petl.fromdicts(attendance_dicts2)
    header = petl.header(return_table)
    if 'Event Name' in header:
        return_table = petl.cut(return_table, 'Full Name', 'Event Name', 'Time', 'Week Num', 'Date', 'Event ID',
            'Individual ID')
    else:
        return_table = petl.cut(return_table, 'Date', 'Event ID', 'Individual ID')

    return return_table


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


if __name__ == "__main__":
    main(sys.argv[1:])
