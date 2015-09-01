#!/usr/bin/env python


import sys, os.path, csv, argparse, petl, re, datetime, time, shutil, tempfile


# Fake class only for purpose of limiting global namespace to the 'g' object
class g:
    args = None
    xref_member_fields = None
    xref_how_sourced = None
    xref_w2s_skills_sgifts = None
    hitmiss_counters = None
    semicolon_sep_fields = None
    header_comments = None
    conversion_traces = None
    conversion_row_num = None
    start_conversion_time = None
    total_rows = None


def main(argv):

    global g

    parser = argparse.ArgumentParser()
    parser.add_argument("--individuals-filename", required=True, help="Input CSV with individuals data dumped " \
        "from Servant Keeper")
    parser.add_argument("--child-approvals-filename", required=True, help="Filename of CSV file listing approval " \
        "dates that individuals got various clearances to work with children")
    parser.add_argument("--output-filename", required=True, help="Output CSV filename which will be loaded with " \
        "individuals data in CCB import format ")
    parser.add_argument('--trace', action='store_true', help="If specified, prints to stdout as new columns are "
        "added")
    g.args = parser.parse_args()

    if not os.path.isfile(g.args.individuals_filename):
        print >> sys.stderr, "Error: cannot open file '" + g.args.individuals_filename + "'"
        sys.exit(1)

    table = petl.fromcsv(g.args.individuals_filename)

    # Rename the first and second 'General Notes' columns to be 'Family Notes' and 'Individual Notes' respectively
    header_row = petl.header(table)
    gen_notes_column_indices = [x for x in range(len(header_row)) if header_row[x] == 'General Notes']
    table = petl.rename(table, {
        gen_notes_column_indices[0]: 'Family Notes',
        gen_notes_column_indices[1]: 'Individual Notes'})

    # Do the xref mappings specified in 'XRef-Member Status' tab of mapping spreadsheet
    g.xref_member_fields = get_xref_member_fields()

    # Do single xref mapping specified in 'XRef-How Sourced' tab of mapping spreadsheet
    g.xref_how_sourced = get_xref_how_sourced()

    # Do xref mappings specified in 'XRef-W2S, Skills, SGifts' tab of mapping spreadsheet
    g.xref_w2s_skills_sgifts = get_xref_w2s_skills_sgifts()
    g.semicolon_sep_fields = {}
    init_hitmiss_counters(g.xref_w2s_skills_sgifts)
    gather_semicolon_sep_field(g.semicolon_sep_fields, table, 'Willing to Serve')
    gather_semicolon_sep_field(g.semicolon_sep_fields, table, 'Skills')
    gather_semicolon_sep_field(g.semicolon_sep_fields, table, 'Spiritual Gifts')

    # print hitmiss_counters
    # for sk_field in hitmiss_counters:
    #    for item in hitmiss_counters[sk_field]:
    #        print >> sys.stderr, sk_field + ';' + item + ';' + str(hitmiss_counters[sk_field][item])

    trace('SETTING UP COLUMNS FOR CONVERSION...', banner=True)

    table = setup_column_conversions(table)

    trace('BEGINNING CONVERSION, THEN EMITTING TO CSV FILE...', banner=True)

    petl.tocsv(table, g.args.output_filename)

    insert_header_comments(table, g.args.output_filename)

    trace('OUTPUT TO CSV COMPLETE.  DONE!', banner=True)


def insert_header_comments(table, filename):
    global g
    table_header = petl.header(table)
    prepended_header = [g.header_comments[x] if x in g.header_comments else '' for x in table_header]
    with tempfile.NamedTemporaryFile(delete=False) as temp:
        tmp_filename = temp.name
        temp.close()
    with open(tmp_filename, 'wb') as csvfile_w:
        csv_writer = csv.writer(csvfile_w)
        csv_writer.writerow(prepended_header)
        with open(filename, 'rb') as csvfile_r:
            csv_reader = csv.reader(csvfile_r)
            for row in csv_reader:
                csv_writer.writerow(row)
    os.rename(filename, filename+'.bak')
    os.rename(tmp_filename, filename)


def trace(msg_str, banner=False):
    global g
    if g.args.trace:
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


#######################################################################################################################
# 'XRef-XRef-W2S, Skills, SGifts' semi-colon field gathering
#######################################################################################################################

def gather_semicolon_sep_field(semicolon_sep_fields, table, field_name):
    global g

    if not field_name in g.xref_w2s_skills_sgifts:
        print >> sys.stderr, '*** Unknown Servant Keeper field: ' + field_name
        sys.exit(1)
    non_blank_rows = petl.selectisnot(table, field_name, u'')
    for indiv_id2semi_sep in petl.values(non_blank_rows, 'Individual ID', field_name):
        individual_id = indiv_id2semi_sep[0]
        list_skills_gifts = [x.strip() for x in indiv_id2semi_sep[1].split(';')]
        for skill_gift in list_skills_gifts:
            if skill_gift in g.xref_w2s_skills_sgifts[field_name]:
                ccb_area = g.xref_w2s_skills_sgifts[field_name][skill_gift][0]
                ccb_flag_to_set = g.xref_w2s_skills_sgifts[field_name][skill_gift][1]
                if not individual_id in g.semicolon_sep_fields:
                    semicolon_sep_fields[individual_id] = {
                        'spiritual gifts': set(),
                        'passions': set(),
                        'abilities': set()
                    }
                g.semicolon_sep_fields[individual_id][ccb_area].add(ccb_flag_to_set)
                record_hitmiss(field_name, skill_gift, 1)
            else:
                record_hitmiss(field_name, skill_gift, -1)


#######################################################################################################################
# 'XRef-XRef-W2S, Skills, SGifts' field mappings
#######################################################################################################################

def get_xref_w2s_skills_sgifts():
    xref_w2s_skills_sgifts_mappings = {
        'Willing to Serve':
        {
            'Acts of God Drama Ministry': ('passions', 'Activity: Drama'),
            'Bake or Prepare Food': ('abilities', 'Skill: Cooking/Baking'),
            'Choir': ('abilities', 'Arts: Vocalist'),
            'Faith Place': ('passions', 'People: Children'),
            'High-School Small-Group Facilitator': ('passions', 'People: Young Adults'),
            'High-School Youth Group Ldr/Chaperone': ('passions', 'People: Young Adults'),
            'Kids Zone': ('passions', 'People: Children'),
            'Liturgical Dance Ministry': ('abilities', 'Arts: Dance'),
            'Middle-School Small-Group Facilitator': ('passions', 'People: Children'),
            'Middle-School Youth Group Ldr/Chaperone': ('passions', 'People: Children'),
            'Nursery Helper': ('passions', 'People: Infants/Toddlers'),
            'Outreach - International - Mission trip': ('passions', 'Activity: Global Missions'),
            'Outreach - Local - for adults': ('passions', 'Activity: Local Outreach'),
            'Outreach - Local - for familiies/children': ('passions', 'Activity: Local Outreach'),
            'Outreach - Local - Mission trip': ('passions', 'Activity: Local Outreach'),
            'Outreach - U.S. - Mission trip': ('passions', 'Activity: Regional Outreach'),
            'Vacation Bible School': ('passions', 'People: Children'),
            'Visit home-bound individuals': ('passions', 'People: Seniors')
        },
        'Skills':
        {
            'Compassion / Listening Skills': ('abilities', 'Skill: Counseling'),
            'Cooking / Baking': ('abilities', 'Skill: Cooking/Baking'),
            'Dancer / Choreographer': ('abilities', 'Arts: Dance'),
            'Drama': ('passions', 'Activity: Drama'),
            'Encouragement': ('spiritual gifts', 'Encouragement'),
            'Gardening / Yard Work': ('abilities', 'Skill: Gardening'),
            'Giving': ('spiritual gifts', 'Giving'),
            'Information Technology': ('abilities', 'Skill: Tech/Computers'),
            'Mailing Preparation': ('abilities', 'Skill: Office Admin'),
            'Organizational Skills': ('abilities', 'Skill: Office Admin'),
            'Photography / Videography': ('abilities', 'Arts: Video/Photography'),
            'Prayer': ('spiritual gifts', 'Intercession'),
            'Sew / Knit / Crochet': ('abilities', 'Arts: Sew/Knit/Crochet'),
            'Singer': ('abilities', 'Arts: Vocalist'),
            'Teacher': ('abilities', 'Skill: Education'),
            'Writer': ('abilities', 'Arts: Writer')
        },
        'Spiritual Gifts':
        {
            'Administration': ('spiritual gifts', 'Administration'),
            'Apostleship': ('spiritual gifts', 'Apostleship'),
            'Craftsmanship': ('spiritual gifts', 'Craftsmanship'),
            'Discernment': ('spiritual gifts', 'Discernment'),
            'Encouragement': ('spiritual gifts', 'Encouragement'),
            'Evangelism': ('spiritual gifts', 'Evangelism'),
            'Faith': ('spiritual gifts', 'Faith'),
            'Giving': ('spiritual gifts', 'Giving'),
            'Helps': ('spiritual gifts', 'Helps'),
            'Hospitality': ('spiritual gifts', 'Hospitality'),
            'Intercession': ('spiritual gifts', 'Intercession'),
            'Word of Knowledge': ('spiritual gifts', 'Knowledge'),
            'Leadership': ('spiritual gifts', 'Leadership'),
            'Mercy': ('spiritual gifts', 'Mercy'),
            'Prophecy': ('spiritual gifts', 'Prophecy'),
            'Teaching': ('spiritual gifts', 'Teaching'),
            'Word of Wisdom': ('spiritual gifts', 'Wisdom')
        }
    }
    return xref_w2s_skills_sgifts_mappings


#######################################################################################################################
# 'XRef-XRef-W2S, Skills, SGifts' hit-miss helper functions
#######################################################################################################################

def init_hitmiss_counters(xref_w2s_skills_sgifts_mappings):
    global g
    g.hitmiss_counters = {}
    for sk_field in xref_w2s_skills_sgifts_mappings:
        g.hitmiss_counters[sk_field] = {}
        for item in xref_w2s_skills_sgifts_mappings[sk_field]:
            g.hitmiss_counters[sk_field][item] = 0


def record_hitmiss(sk_field, item, count):
    global g
    if not sk_field in g.hitmiss_counters:
        g.hitmiss_counters[sk_field] = {}
    if not item in g.hitmiss_counters[sk_field]:
        g.hitmiss_counters[sk_field][item] = 0
    g.hitmiss_counters[sk_field][item] += count


#######################################################################################################################
# 'XRef-How Sourced' mapping behaviors declaration
#######################################################################################################################

def get_xref_how_sourced():
    xref_how_sourced = {
        'Attendance Roster': '',
        'Connect Card': '',
        'Moved to New Family': '',
        'New Member Class': '',
        'Acts of God': 'Event: Acts of God',
        'Vacation Bible School': 'Event: Children',
        'Donation - Ingomar Living Water': 'Event: Living Water',
        'Rummage Sale': 'Event: Rummage Sale',
        'Wellness Ministry': 'Event: Wellness',
        'Philippi': 'Event: Youth',
        'Youth Group': 'Event: Youth',
        'Baptism': 'Other',
        'Donation - Non-Outreach': 'Other',
        'Other': 'Other',
        'Small Group': 'Small Group',
        '': ''
    }
    return xref_how_sourced


#######################################################################################################################
# 'XRef-Member Status' mapping behaviors declaration
#######################################################################################################################

def get_xref_member_fields():
    xref_member_fields = {
        'Active Member': {
            'membership type': 'Member - Active',
            'inactive/remove': '',
            'membership date': get_date_joined,
            'reason left': '',
            'membership stop date': '',
            'deceased': ''
        },
        'Inactive Member': {
            'membership type': 'Member - Inactive',
            'inactive/remove': '',
            'membership date': get_date_joined,
            'reason left': '',
            'membership stop date': '',
            'deceased': ''
        },
        'Regular Attendee': {
            'membership type': 'Regular Attendee',
            'inactive/remove': '',
            'membership date': '',
            'reason left': '',
            'membership stop date': '',
            'deceased': ''
        },
        'Visitor': {
            'membership type': 'Guest',
            'inactive/remove': '',
            'membership date': '',
            'reason left': '',
            'membership stop date': '',
            'deceased': ''
        },
        'Non-Member': {
            'membership type': get_sourced_donor,
            'inactive/remove': '',
            'membership date': '',
            'reason left': '',
            'membership stop date': '',
            'deceased': ''
        },
        'Pastor': {
            'membership type': 'Pastor',
            'inactive/remove': '',
            'membership date': '',
            'reason left': '',
            'membership stop date': '',
            'deceased': ''
        },
        'Deceased - Member': {
            'membership type': 'Member - Inactive',
            'inactive/remove': 'yes',
            'membership date': get_date_joined,
            'reason left': 'Deceased',
            'membership stop date': '',
            'deceased': get_date_of_death
        },
        'Deceased - Non-Member': {
            'membership type': 'Friend',
            'inactive/remove': 'yes',
            'membership date': '',
            'reason left': '',
            'membership stop date': '',
            'deceased': get_date_of_death
        },
        'None': {
            'membership type': '',
            'inactive/remove': 'yes',
            'membership date': '',
            'reason left': '',
            'membership stop date': '',
            'deceased': ''
        },
        'No Longer Attend': {
            'membership type': 'Friend',
            'inactive/remove': '',
            'membership date': '',
            'reason left': 'No Longer Attend',
            'membership stop date': '',
            'deceased': ''
        },
        'Transferred out to other UMC': {
            'membership type': 'Friend',
            'inactive/remove': 'yes',
            'membership date': get_date_joined,
            'reason left': 'Transferred out to other UMC',
            'membership stop date': get_trf_out_date,
            'deceased': ''
        },
        'Transferred out to Non UMC': {
            'membership type': 'Friend',
            'inactive/remove': 'yes',
            'membership date': get_date_joined,
            'reason left': 'Transferred out to Non UMC',
            'membership stop date': get_trf_out_date,
            'deceased': ''
        },
        'Withdrawal': {
            'membership type': 'Friend',
            'inactive/remove': '',
            'membership date': get_date_joined,
            'reason left': 'Withdrawal',
            'membership stop date': get_trf_out_date,
            'deceased': ''
        },
        'Charge Conf. Removal': {
            'membership type': 'Friend',
            'inactive/remove': 'yes',
            'membership date': get_date_joined,
            'reason left': 'Charge Conf. Removal',
            'membership stop date': get_trf_out_date,
            'deceased': ''
        },
        'Archives (Red Book)': {
            'membership type': '',
            'inactive/remove': 'yes',
            'membership date': '',
            'reason left': 'Archives (Red Book)',
            'membership stop date': '',
            'deceased': ''
        },
        '': {  # Remove this entry...only for Hudson Community Foundation
            'membership type': '',
            'inactive/remove': 'yes',
            'membership date': '',
            'reason left': '',
            'membership stop date': '',
            'deceased': ''
        }
    }
    return xref_member_fields


#######################################################################################################################
# 'XRef-Member Status' row getter utilities
#######################################################################################################################

def get_sourced_donor(row):
    if row['How Sourced?'][:8] == 'Donation':
        return 'Donor'
    else:
        return 'Friend'


def get_date_joined(row):
    return row['Date Joined']


def get_trf_out_date(row):
    return row['Trf out/Withdrawal Date']


def get_date_of_death(row):
    return row['Date of Death']


#######################################################################################################################
# Field converter helpers
#######################################################################################################################

def conversion_trace(row, msg_str, sk_col_name, ccb_col_name):
    global g
    indiv_id = row['Individual ID']
    if indiv_id not in g.conversion_traces:
        g.conversion_traces[indiv_id] = []
    member_str = "Member '" + row['Last Name'] + ", " + row['First Name']
    if row['Middle Name'] != '':
        member_str += " " + row['Middle Name']
    member_str += "' (" + row['Individual ID'] + "). "
    if sk_col_name is not None:
        prefix_str = "Mapping from SK column '" + sk_col_name + "' to CCB column '" + \
            ccb_col_name + "'. "
    else:
        prefix_str = "Converting blank '" + ccb_col_name + "'. "
    g.conversion_traces[indiv_id].append(prefix_str + msg_str)
    trace('*** Conversion warning. ' + member_str + prefix_str + msg_str)


def conversion_using_dict_map(row, value, sk_col_name, ccb_col_name, convert_dict, other, trace_other=False):
    if value in convert_dict:
        return convert_dict[value]
    elif other is not None:
        if trace_other and other:
            conversion_trace(row, "'" + value + "' is not a valid '" + ccb_col_name + "', so set to '" + other + "'.",
                 sk_col_name, ccb_col_name)
        return other
    else:
        raise KeyError(value)


def conversion_tracker(row):
    global g
    g.conversion_row_num += 1
    if g.conversion_row_num % 500 == 0:
        if g.args.trace:
            elapsed_time_in_secs = int(time.time() - g.start_conversion_time)
            remaining_secs = (g.total_rows - g.conversion_row_num) * elapsed_time_in_secs / g.conversion_row_num
            trace('CONVERSION PROGRESS: Row ' + str(g.conversion_row_num) + ' of ' + str(g.total_rows) + \
                '. Estimated ' + str(remaining_secs) + ' seconds remaining.', banner=True)


def init_conversion_tracker(table):
    global g
    g.conversion_row_num = 1
    g.start_conversion_time = time.time()
    g.total_rows = petl.nrows(table)


def is_phone_valid(phone_string):
    regex_phone = r'^\d{3}\-\d{3}\-\d{4}$'
    match = re.search(regex_phone, phone_string)
    if match is not None:
        return True
    else:
        return False


def xref_member_field_value(row, field_str):
    global g
    new_value = g.xref_member_fields[row['Member Status']][field_str]
    if callable(new_value):
        new_value = new_value(row)
    return new_value


def xref_w2s_gather(row, gather_str):
    global g
    indiv_id = row['Individual ID']
    if indiv_id in g.semicolon_sep_fields:
        return ';'.join(g.semicolon_sep_fields[indiv_id][gather_str])
    else:
        return ''

    
#######################################################################################################################
# Field converter methods (convert_xyz)
#######################################################################################################################

def convert_date(value, row, sk_col_name, ccb_col_name):
    """If this field is of exact format 'm/d/yyyy', and 'm', 'd', and 'yyyy' represent a valid date, it is retained,
    else it is set to blank ('')."""

    try:
        d = datetime.datetime.strptime(value.strip(), '%m/%d/%Y')
        new_value = d.strftime('%Y-%m-%d')
    except ValueError:
        new_value = ''
    except:
        raise
    if new_value == '' and not re.match(r'(\s+/\s+/\s+)|(^$)', value):
        conversion_trace(row, "Blanked invalid date: '" + value + "'", sk_col_name, ccb_col_name)
    return new_value


def convert_phone(value, row, sk_col_name, ccb_col_name):
    """If this field is of exact format 'nnn-nnn-nnnn', it is retained, else it is set to blank ('')."""

    if is_phone_valid(value):
        new_value = value
    else:
        new_value = ''
        if not re.match(r'\s+\-\s+\-\s+', value):
            conversion_trace(row, "Blanked invalid phone number: '" + value + "'", sk_col_name, ccb_col_name)
    return new_value


def convert_family_position(value, row, sk_col_name, ccb_col_name):
    """This field is remapped as follows:
        'Head of Household' -> 'Primary contact',
        'Spouse' -> 'Spouse',
        'Son' -> 'Child',
        'Daughter' -> 'Child',
        <anything_else> -> 'Other'."""

    # This tracker could be placed in *any* one and only one convert_xxx() method to figure out progress.
    # This one was randomly chosen
    #
    # NOTE:  PETL has petl.progress() and other supporting methods to do progress tracking
    conversion_tracker(row)

    convert_dict = {
        'Head of Household': 'Primary contact',
        'Spouse': 'Spouse',
        'Son': 'Child',
        'Daughter': 'Child'
    }
    return conversion_using_dict_map(row, value, sk_col_name, ccb_col_name, convert_dict, 'Other', trace_other=True)


def convert_prefix(value, row, sk_col_name, ccb_col_name):
    """This field is remapped as follows:
        'Rev.' -> 'Rev.',
        'Dr.' -> 'Dr.',
        'Mr.' -> 'Mr.',
        'Pastor' -> 'Pastor',
        'Ms.' -> 'Ms.',
        'Mrs.' -> 'Mrs.',
        <anything_else> -> blank ('')."""

    convert_dict = {
        'Rev.': 'Rev.',
        'Dr.': 'Dr.',
        'Mr.': 'Mr.',
        'Pastor': 'Pastor',
        'Ms.': 'Ms.',
        'Mrs.': 'Mrs.'
    }
    return conversion_using_dict_map(row, value, sk_col_name, ccb_col_name, convert_dict, '', trace_other=True)


def convert_suffix(value, row, sk_col_name, ccb_col_name):
    """This field is remapped as follows:
        'Jr.' -> 'Jr.',
        'Sr.' -> 'Sr.',
        'II' -> 'II',
        'III' -> 'III',
        'IV' -> 'IV',
        'Dr.' -> 'Dr.',
        <anything_else> -> blank ('')."""

    convert_dict = {
        'Jr.': 'Jr.',
        'Sr.': 'Sr.',
        'II': 'II',
        'III': 'III',
        'IV': 'IV',
        'Dr.': 'Dr.',
    }
    return conversion_using_dict_map(row, value, sk_col_name, ccb_col_name, convert_dict, '', trace_other=True)


def convert_limited_access_user(value, row, sk_col_name, ccb_col_name):
    """By setting to 'no', we intend all users to be 'Basic User'."""

    return 'no'


def convert_listed(value, row, sk_col_name, ccb_col_name):
    """By setting to 'yes', we intend all users to be visible / 'Listed' (except those auto-limited by birthday date
    and age detection in CCB, of course)."""

    return 'yes'


def convert_contact_phone(value, row, sk_col_name, ccb_col_name):
    """This field is loaded with 'home phone' value if it's a valid phone number, else 'cell phone' if that's valid,
    and if neither 'home phone' nor 'cell phone' are valid, then this field is blank"""

    home_phone_valid = is_phone_valid(row['Home Phone'])
    cell_phone_valid = is_phone_valid(row['Cell Phone'])
    if home_phone_valid:
        return row['Home Phone']
    elif cell_phone_valid:
        return row['Cell Phone']
    else:
        return ''


def convert_gender(value, row, sk_col_name, ccb_col_name):
    """This field is loaded with 'male' or 'female', or with '' if unknown/other value in Servant Keeper."""

    convert_dict = {
        'Male': 'male',
        'Female': 'female'
    }
    return conversion_using_dict_map(row, value, sk_col_name, ccb_col_name, convert_dict, '', trace_other=True)


def convert_marital_status(value, row, sk_col_name, ccb_col_name):
    """This field is remapped as follows:
        'Divorced' -> 'divorced',
        'Separated' -> 'separated',
        'Married' -> 'married',
        'Single' -> 'single',
        'Widowed' -> 'widowed'
        <anything_else> -> blank ('')."""

    convert_dict = {
        'Divorced': 'divorced',
        'Separated': 'separated',
        'Married': 'married',
        'Single': 'single',
        'Widowed': 'widowed'
    }
    return conversion_using_dict_map(row, value, sk_col_name, ccb_col_name, convert_dict, '', trace_other=True)


def convert_membership_date(value, row, sk_col_name, ccb_col_name):
    """If person was *ever* a member current or prior (i.e. Servant Keeper's 'Member Status' is one of:
    'Active Member', 'Inactive Member', 'Deceased - Member', 'Transferred out to other UMC',
    'Transferred out to Non UMC', 'Withdrawal', 'Charge Conf. Removal'), and Servant Keeper's 'Date Joined' field
    is a valid date, then this date is set Servant Keeper's 'Date Joined', else it is set to blank ('')"""

    new_value = xref_member_field_value(row, 'membership date')
    return convert_date(new_value, row, sk_col_name, ccb_col_name)


def convert_membership_stop_date(value, row, sk_col_name, ccb_col_name):
    """If person was a prior member (i.e. Servant Keeper's 'Member Status' is one of: 'Transferred out to other UMC',
    'Transferred out to Non UMC', 'Withdrawal', 'Charge Conf. Removal'), and Servant Keeper's
    'Trf out/Withdrawal Date' field is a valid date, then this date is set to Servant Keeper's
    'Trf out/Withdrawal Date', else it is set to blank ('')"""

    new_value = xref_member_field_value(row, 'membership stop date')
    return convert_date(new_value, row, sk_col_name, ccb_col_name)


def convert_membership_type(value, row, sk_col_name, ccb_col_name):
    """This field has a complex mapping which is basically as follows:
        'Active Member' -> 'Member - Active',
        'Inactive Member' -> 'Member - Inactive',
        'Regular Attendee' -> 'Regular Attendee',
        'Visitor' -> 'Guest',
        'Non-Member (How Sourced ? <> 'Donation...')' -> 'Friend',
        'Non-Member (How Sourced ? == 'Donation...')' -> 'Donor',
        'Pastor' -> 'Pastor',
        'Deceased - Member' -> 'Member - Inactive',
        'Deceased - Non-Member' -> 'Friend',
        'None' -> '' (blank),
        'No Longer Attend' -> 'Friend',
        'Transferred out to other UMC' -> 'Friend',
        'Transferred out to Non UMC' -> 'Friend',
        'Withdrawal' -> 'Friend',
        'Charge Conf. Removal' -> 'Friend'
        'Archives (Red Book)' -> '' (blank)."""

    global g
    new_value = g.xref_member_fields[row['Member Status']]['membership type']
    if callable(new_value):
        new_value = new_value(row)
    return new_value


def convert_country(value, row, sk_col_name, ccb_col_name):
    """This field is mapped as follows:
    'UK' -> 'United Kingdom',
    <anything_else> -> <original_value>"""

    if value == 'UK':
        return 'United Kingdom'
    else:
        return value


def convert_inactive_remove(value, row, sk_col_name, ccb_col_name):
    """Based on the following values of Servant Keeper's 'Member Status' field, this field is mapped as follows:
        'Active Member' -> blank ('', i.e. active so retain),
        'Inactive Member' -> blank ('', i.e. active so retain),
        'Regular Attendee' -> blank ('', i.e. active so retain),
        'Visitor' -> blank ('', i.e. active so retain),
        'Non-Member (How Sourced ? <> 'Donation...')' -> blank ('', i.e. active so retain),
        'Non-Member (How Sourced ? == 'Donation...')' -> blank ('', i.e. active so retain),
        'Pastor' -> blank ('', i.e. active so retain),
        'Deceased - Member' -> 'yes' (i.e. inactive so remove),
        'Deceased - Non-Member' -> 'yes' (i.e. inactive so remove),
        'None' -> 'yes' (i.e. inactive so remove),
        'No Longer Attend' -> blank ('', i.e. active so retain),
        'Transferred out to other UMC' -> 'yes' (i.e. inactive so remove),
        'Transferred out to Non UMC' -> 'yes' (i.e. inactive so remove),
        'Withdrawal' -> blank ('', i.e. active so retain)...AndyF comment - shouldn't this become remove/inactive???,
        'Charge Conf. Removal' -> 'yes' (i.e. inactive so remove),
        'Archives (Red Book)' -> 'yes' (i.e. inactive so remove)."""

    global g
    new_value = g.xref_member_fields[row['Member Status']]['inactive/remove']
    return new_value


def convert_baptized(value, row, sk_col_name, ccb_col_name):
    """This field is remapped as follows:
        'Yes' -> 'yes',
        'No' -> 'no'.
    I.e., the selections are just made lower case."""

    convert_dict = {
        'Yes': 'yes',
        'No': 'no'
    }
    return conversion_using_dict_map(row, value, sk_col_name, ccb_col_name, convert_dict, None)


def convert_notes(value, row, sk_col_name, ccb_col_name):
    """This field is formed from both 'Family Notes' (1st 'General Notes') and 'Individual Notes' (2nd 'General Notes')
    fields from Servant Keeper.  It is pre-pended by language indicating it's from Servant Keeper 'General Notes' and
    with a date-time stamp of the time that transform utility was run.  The separate notes sections are pre-pended
    with 'FAMILY NOTES:' (if present and if this individual is 'Primary Contact') and 'INDIVIDUAL NOTES:' (if
    present)."""

    family_notes_str = None
    individual_notes_str = None
    # TODO - if we decide to count every family with only one individual as 'Primary' contact, then logic below
    # changes (not looking up 'Relationship' == 'Head of Household' in Servant Keeper)
    if row['Relationship'] == 'Head of Household' and row['Family Notes']:
        family_notes_str = '\n\nSERVANT KEEPER FAMILY NOTES:\n\n' + row['Family Notes']
    if row['Individual Notes']:
        individual_notes_str = '\n\nSERVANT KEEPER INDIVIDUAL NOTES:\n\n' + row['Individual Notes']
    if family_notes_str or individual_notes_str:
        output_str = 'THESE NOTES WERE CONVERTED FROM SERVANT KEEPER ({})'.format(
            datetime.datetime.now().strftime('%Y-%m-%d %H:%M'))
        if family_notes_str:
            output_str += family_notes_str
        if individual_notes_str:
            output_str += individual_notes_str
        #print '-->\n' + output_str + '\n<--\n'
        return output_str
    else:
        #print '-->\n<--\n'
        return ''


def convert_approved_to_work_with_children(value, row, sk_col_name, ccb_col_name):
    # TODO
    return ''


def convert_approved_to_work_with_children_stop_date(value, row, sk_col_name, ccb_col_name):
    # TODO
    return ''


def convert_how_they_heard(value, row, sk_col_name, ccb_col_name):
    """This field is mapped based on Servant Keeper's 'How Sourced' column as follows:
        'Acts of God' -> 'Event: Acts of God',
        'Vacation Bible School' -> 'Event: Children',
        'Donation - Ingomar Living Water' -> 'Event: Living Water',
        'Rummage Sale' -> 'Event: Rummage Sale',
        'Wellness Ministry' -> 'Event: Wellness',
        'Philippi' -> 'Event: Youth',
        'Youth Group' -> 'Event: Youth',
        'Baptism' -> 'Other',
        'Donation - Non-Outreach' -> 'Other',
        'Other' -> 'Other',
        'Small Group' -> 'Small Group'."""

    global g
    value = g.xref_how_sourced[row['How Sourced?']]
    return value


def convert_how_they_joined(value, row, sk_col_name, ccb_col_name):
    """This field is remapped as follows:
        'Associate' -> 'Associate',
        'Confirmation' -> 'Confirmation',
        'Membership Restored' -> 'Membership Restored',
        'Profession of Faith' -> 'Profession of Faith',
        'Transferred  from other UMC' -> 'Transferred from other UMC',
        'Transferred from Non UMC' -> 'Transferred from Non UMC',
        '' -> ''.
    Note:  the *only* remapping happening above is removal of extra space from 'Transferred  from other UMC'
    setting."""

    convert_dict = {
        'Associate': 'Associate',
        'Confirmation': 'Confirmation',
        'Membership Restored': 'Membership Restored',
        'Profession of Faith': 'Profession of Faith',
        'Transferred  from other UMC': 'Transferred from other UMC',
        'Transferred from Non UMC': 'Transferred from Non UMC',
        '': ''
    }
    return conversion_using_dict_map(row, value, sk_col_name, ccb_col_name, convert_dict, None)


def convert_reason_left_church(value, row, sk_col_name, ccb_col_name):
    """If person was formerly a member or regular attender (i.e. Servant Keeper's 'Member Status' is one of:
    'Deceased - Member', 'No Longer Attend', 'Transferred out to other UMC', 'Transferred out to Non UMC',
    'Withdrawal', 'Withdrawal', 'Archives (Red Book)'), then this field is mapped from Servant Keeper's
    'Member Status' field as follows:
        'Deceased - Member' -> 'Deceased',
        'No Longer Attend' -> 'No Longer Attend',
        'Transferred out to other UMC' -> 'Transferred out to other UMC',
        'Transferred out to Non UMC' -> 'Transferred out to Non UMC',
        'Withdrawal' -> 'Withdrawal',
        'Charge Conf. Removal' -> 'Charge Conf. Removal',
        'Archives (Red Book)', -> 'Archives (Red Book)'."""

    global g
    value = g.xref_member_fields[row['Member Status']]['reason left']
    return value


def convert_deceased(value, row, sk_col_name, ccb_col_name):
    """If person was a member or non-member who has died (i.e. Servant Keeper's 'Member Status' field is one of:
    'Deceased - Member', 'Deceased - Non-Member'), and Servant Keeper's 'Date of Death' field is a valid date,
    then this field is set to Servant Keeper's 'Date of Death' field, else it is set to blank ('')."""

    new_value = xref_member_field_value(row, 'deceased')
    return convert_date(new_value, row, sk_col_name, ccb_col_name)


def convert_spiritual_gifts(value, row, sk_col_name, ccb_col_name):
    """This field is mapped based on *both* Servant Keeper's 'Skills' and 'Spiritual Gifts' fields as follows:
        SK Skills 'Encouragement' -> 'Encouragement',
        SK Skills 'Giving' -> 'Giving',
        SK Skills 'Prayer' -> 'Intercession',
        SK Spiritual Gifts 'Administration' -> 'Administration',
        SK Spiritual Gifts 'Apostleship' -> 'Apostleship',
        SK Spiritual Gifts 'Craftsmanship' -> 'Craftsmanship',
        SK Spiritual Gifts 'Discernment' -> 'Discernment',
        SK Spiritual Gifts 'Encouragement' -> 'Encouragement',
        SK Spiritual Gifts 'Evangelism' -> 'Evangelism',
        SK Spiritual Gifts 'Faith' -> 'Faith',
        SK Spiritual Gifts 'Giving' -> 'Giving',
        SK Spiritual Gifts 'Helps' -> 'Helps',
        SK Spiritual Gifts 'Hospitality' -> 'Hospitality',
        SK Spiritual Gifts 'Intercession' -> 'Intercession',
        SK Spiritual Gifts 'Knowledge' -> 'Knowledge',
        SK Spiritual Gifts 'Leadership' -> 'Leadership',
        SK Spiritual Gifts 'Mercy' -> 'Mercy',
        SK Spiritual Gifts 'Prophecy' -> 'Prophecy',
        SK Spiritual Gifts 'Teaching' -> 'Teaching',
        SK Spiritual Gifts 'Wisdom' -> 'Wisdom'."""

    return xref_w2s_gather(row, 'spiritual gifts')


def convert_passions(value, row, sk_col_name, ccb_col_name):
    """This field is mapped based on *both* Servant Keeper's 'Willing to Serve' and 'Skills' fields as follows:
        SK Willing to Serve 'Acts of God Drama Ministry' -> 'Activity: Drama',
        SK Willing to Serve 'Faith Place' -> 'People: Children',
        SK Willing to Serve 'High-School Small-Group Facilitator' -> 'People: Young Adults',
        SK Willing to Serve 'High-School Youth Group Ldr/Chaperone' -> 'People: Young Adults',
        SK Willing to Serve 'Kids Zone' -> 'People: Children',
        SK Willing to Serve 'Middle-School Small-Group Facilitator' -> 'People: Children',
        SK Willing to Serve 'Middle-School Youth Group Ldr/Chaperone' -> 'People: Children',
        SK Willing to Serve 'Nursery Helper' -> 'People: Infants/Toddlers',
        SK Willing to Serve 'Outreach - International - Mission trip' -> 'Activity: Global Missions',
        SK Willing to Serve 'Outreach - Local - for adults' -> 'Activity: Local Outreach',
        SK Willing to Serve 'Outreach - Local - for familiies/children' -> 'Activity: Local Outreach',
        SK Willing to Serve 'Outreach - Local - Mission trip' -> 'Activity: Local Outreach',
        SK Willing to Serve 'Outreach - U.S. - Mission trip' -> 'Activity: Regional Outreach',
        SK Willing to Serve 'Vacation Bible School' -> 'People: Children',
        SK Willing to Serve 'Visit home-bound individuals' -> 'People: Seniors',
        SK Skills 'Drama' -> 'Activity: Drama'."""

    return xref_w2s_gather(row, 'passions')


def convert_abilities_skills(value, row, sk_col_name, ccb_col_name):
    """This field is mapped based on *both* Servant Keeper's 'Willing to Serve' and 'Skills' fields as follows:
        SK Willing to Serve 'Bake or Prepare Food' -> 'Skill: Cooking/Baking',
        SK Willing to Serve 'Choir' -> 'Arts: Vocalist',
        SK Willing to Serve 'Liturgical Dance Ministry' -> 'Arts: Dance',
        SK Skills 'Compassion / Listening Skills' -> 'Skill: Counseling',
        SK Skills 'Cooking / Baking' -> 'Skill: Cooking/Baking',
        SK Skills 'Dancer / Choreographer' -> 'Arts: Dance',
        SK Skills 'Gardening / Yard Work' -> 'Skill: Gardening',
        SK Skills 'Information Technology' -> 'Skill: Tech/Computers',
        SK Skills 'Mailing Preparation' -> 'Skill: Office Admin',
        SK Skills 'Organizational Skills' -> 'Skill: Office Admin',  (this mapping seems funny)
        SK Skills 'Photography / Videography' -> 'Arts: Video/Photography',
        SK Skills 'Sew / Knit / Crochet' -> 'Arts: Sew/Knit/Crochet',
        SK Skills 'Singer' -> 'Arts: Vocalist',
        SK Skills 'Teacher' -> 'Skill: Education',
        SK Skills 'Writer' -> 'Arts: Writer'."""

    return xref_w2s_gather(row, 'abilities')


def convert_confirmed(value, row, sk_col_name, ccb_col_name):
    """This field is remapped as follows:
        'Yes' -> 'yes',
        'No' -> 'no'.
    I.e., the selections are just made lower case."""

    convert_dict = {
        'Yes': 'yes',
        'No': 'no'
    }
    return conversion_using_dict_map(row, value, sk_col_name, ccb_col_name, convert_dict, None)


def convert_spirit_mailing(value, row, sk_col_name, ccb_col_name):
    """This field is remapped as follows:
        'Yes' -> 'postal mail',
        'No' -> 'email'."""

    convert_dict = {
        'Yes': 'postal mail',
        'No': 'email'
    }
    return conversion_using_dict_map(row, value, sk_col_name, ccb_col_name, convert_dict, None)


#######################################################################################################################
# Core utility conversion setup method.
#######################################################################################################################

def setup_column_conversions(table):

    global g

    g.header_comments = {}
    g.conversion_traces = {}

    # Mark start time and number of rows that we're converting
    init_conversion_tracker(table)

    # Layout of field_mappings list of tuples below is:
    #
    # - [0] CCB field name
    #
    # - [1] Source Servant Keeper field name or None if not directly 1:1 derived from a Servant Keeper field
    #
    # - [2] Converter method (applied after field rename if field originates from Servant Keeper)
    #
    # - [3] Custom or process queue field type ('custom-text', 'custom-date', 'custom-pulldown', 'process_queue')
    #   or None if this is not a custom or process queue data field

    field_ccb_name = 0
    field_sk_name = 1
    field_converter_method = 2
    field_custom_or_process_queue = 3

    field_mappings = [

        # Core (silver sample.xls) columns
        ['family id', 'Family ID'],
        ['individual id', 'Individual ID'],
        ['family position', 'Relationship', convert_family_position],
        ['prefix', 'Title', convert_prefix],
        ['first name', 'Preferred Name'],
        ['middle name', 'Middle Name'],
        ['last name', 'Last Name'],
        ['suffix', 'Suffix', convert_suffix],
        ['legal name', 'First Name'],
        ['Limited Access User', None, convert_limited_access_user],
        ['Listed', None, convert_listed],
        ['inactive/remove', 'Active Profile', convert_inactive_remove],
        ['campus', None, 'Ingomar Church'],
        ['email', 'Individual e-Mail'],
        ['mailing street', 'Address'],
        ['mailing street line 2', 'Address Line 2'],
        ['city', 'City'],
        ['state', 'State'],
        ['postal code', 'Zip Code'],
        ['country', 'Country', convert_country],
        ['mailing carrier route'],
        ['home street', 'Address'],
        ['home street line 2', 'Address Line 2'],
        ['home_city', 'City'],
        ['home_state', 'State'],
        ['home_postal code', 'Zip Code'],
        ['area_of_town'],
        ['contact_phone', None, convert_contact_phone],
        ['home phone', 'Home Phone', convert_phone],
        ['work phone', 'Work Phone', convert_phone],
        ['cell phone', 'Cell Phone', convert_phone],
        ['service provider'],
        ['fax'],
        ['pager'],
        ['emergency phone'],
        ['emergency contact name'],
        ['birthday', 'Birth Date', convert_date],
        ['anniversary', 'Wedding Date', convert_date],
        ['gender', 'Gender', convert_gender],
        ['giving #', 'Env #'],
        ['marital status', 'Marital Status', convert_marital_status],
        ['membership date', 'Date Joined', convert_membership_date],
        ['membership stop date', 'Trf out/Withdrawal Date', convert_membership_stop_date],
        ['membership type', None, convert_membership_type],
        ['baptized', 'Baptized', convert_baptized],
        ['school', 'School District'],
        ['school grade'],
        ['known allergies'],
        ['confirmed no allergies'],
        ['notes', None, convert_notes],
        ['approved to work with children', None, convert_approved_to_work_with_children],
        ['approved to work with children stop date', None, convert_approved_to_work_with_children_stop_date],
        ['commitment date'],
        ['how they heard', None, convert_how_they_heard],
        ['how they joined', None, convert_how_they_joined],
        ['reason left church', None, convert_reason_left_church],
        ['job title', 'Occupation'],
        ['work street 1'],
        ['work street 2'],
        ['work city'],
        ['work state'],
        ['work postal code'],
        ['Current Story'],
        ['Commitment Story'],
        ['deceased', 'Date of Death', convert_deceased],
        ['facebook_username'],
        ['twitter_username'],
        ['blog_username'],
        ['website my'],
        ['website work'],
        ['military'],  # Anything from Carol?
        ['spiritual_maturity'],
        ['spiritual_gifts', None, convert_spiritual_gifts],
        ['passions', None, convert_passions],
        ['abilities/skills', None, convert_abilities_skills],
        ['church_services_I_attend'],
        ['personal_style'],

        # No such thing as 'other' address info in silver_sample file, but they're valid fields
        ['other street', 'Alt Address'],
        ['other street line 2', 'Alt Address Line 2'],
        ['other city', 'Alt City'],
        ['other country', 'Alt Country', convert_country],
        ['other state', 'Alt State'],
        ['other_postal code', 'Alt Zip Code'],

        # Guest folloowup process queue
        ['guest_followup 1 month', '1-Month Follow-up', convert_date, 'process_queue'],
        ['guest_followup 1 week', 'Wk 1 Follow-up', convert_date, 'process_queue'],
        ['guest_followup 2 weeks', 'Wk 2 Follow-up', convert_date, 'process_queue'],

        # Burial folloowup process queue
        ['burial city county state', 'Burial: City, County, St', None, 'process_queue'],
        ['burial date', 'Burial: Date', convert_date, 'process_queue'],
        ['burial officiating pastor', 'Burial: Officating Pastor', None, 'process_queue'],
        ['burial site title', 'Burial: Site Title', None, 'process_queue'],

        # Custom fields
        ['baptism date', 'Baptized Date', convert_date, 'custom-pulldown'],
        ['baptized by', 'Baptized by', None, 'custom-pulldown'],
        ['confirmed date', 'Confirmed Date', convert_date, 'custom-date'],
        ['confirmed', 'Confirmed', convert_confirmed, 'custom-pulldown'],
        ['mailbox number', 'Mail Box #', None, 'custom-text'],
        ['spirit mailing', 'The Spirit Mailing', convert_spirit_mailing, 'custom-pulldown'],
        ['photo release', 'Photo Release', None, 'custom-pulldown'],
        ['ethnicity', 'Racial/Ethnic identification', None, 'custom-pulldown'],
        ['church transferred from', 'Church Transferred From', None, 'custom-text'],
        ['church transferred to', 'Church Transferred To', None, 'custom-text'],
        ['pastor when joined', 'Pastor when joined', None, 'custom-text'],
        ['pastor when leaving', 'Pastor when leaving', None, 'custom-text']
    ]

    num_sk_columns = len(petl.header(table))

    for field_map_list in field_mappings:

        val_field_ccb_name = field_map_list[field_ccb_name]
        val_field_sk_name = None
        val_field_converter_method = None
        val_field_custom_or_process_queue = None

        if len(field_map_list) > 1:
            val_field_sk_name = field_map_list[field_sk_name]
        if len(field_map_list) > 2:
            val_field_converter_method = field_map_list[field_converter_method]
        if len(field_map_list) > 3:
            val_field_custom_or_process_queue = field_map_list[field_custom_or_process_queue]

        # Add empty CCB placeholder column with no data to populate it
        if val_field_sk_name is None and val_field_converter_method is None:
            table = add_empty_column(table, val_field_ccb_name)

        # Add cloned and renamed column
        elif val_field_sk_name is not None and val_field_converter_method is None:
            table = add_cloned_column(table, val_field_ccb_name, val_field_sk_name)

        # Add empty or cloned/renamed column and run it through converter method
        elif val_field_sk_name is None and val_field_converter_method is not None:
            if isinstance(val_field_converter_method, basestring):
                table = add_fixed_string_column(table, val_field_ccb_name, val_field_converter_method)
            elif callable(val_field_converter_method):
                table = add_empty_column_then_convert(table, val_field_ccb_name, val_field_converter_method)
            else:
                raise AssertionError("On '" + val_field_ccb_name + "' field, converter method is not callable " \
                    "and not a string")

        # If source SK column is specified, clone it and convert
        elif val_field_sk_name is not None and val_field_converter_method is not None:
            if not callable(val_field_converter_method):
                raise AssertionError("On '" + val_field_ccb_name + "' field, converter method is not callable")
            else:
                table = add_cloned_column_then_convert(table, val_field_ccb_name, val_field_sk_name,
                    val_field_converter_method)

        add_header_comment(val_field_ccb_name,
            get_descriptive_custom_or_process_queue_string(val_field_custom_or_process_queue))

    # This must be 'last' conversion so that it picks up warnings recorded in prior conversions
    table = petl.addfield(table, 'conversion trace', lambda rec: ';'.join(g.conversion_traces[rec['Individual ID']]) \
        if rec['Individual ID'] in g.conversion_traces else '')

    return table


def add_header_comment(val_field_ccb_name, header_str):
    global g
    if not header_str:
        return
    header_str = format_header_comment(header_str)
    if val_field_ccb_name not in g.header_comments:
        g.header_comments[val_field_ccb_name] = header_str
    else:
        g.header_comments[val_field_ccb_name] += ('\n\n' + header_str)


def format_header_comment(header_str):
    """For any line beginning with >4 spaces, chop off all but 4 and post-pend the line with \n"""

    output_str = ''
    prior_line_was_indented = False
    for line in header_str.split('\n'):
        if line[:5] == '     ':
            if not prior_line_was_indented:
                output_str += '\n'
            output_str += line[4:] + '\n'
            prior_line_was_indented = True
        elif line[:4] == '    ':
            output_str += line[4:] + ' '
            prior_line_was_indented = False
        else:
            output_str += line + ' '
            prior_line_was_indented = False
    return output_str
    # return re.sub(r'\s{5}', '\n    ', re.sub(r'\s*\n\s{4}', ' ', header_str))


def get_descriptive_custom_or_process_queue_string(val_field_custom_or_process_queue):
    global g
    if not val_field_custom_or_process_queue:
        return None
    else:
        map_field_to_comment = {
            'custom-pulldown': 'This field is a CCB custom pulldown field.',
            'custom-text': 'This field is a CCB custom text field.',
            'custom-date': 'This field is a CCB custom date field.',
            'process_queue': 'This field is a CCB process queue data field.'
        }
        assert val_field_custom_or_process_queue in map_field_to_comment
        return map_field_to_comment[val_field_custom_or_process_queue]


def add_empty_column(table, val_field_ccb_name):
    assert isinstance(val_field_ccb_name, basestring)
    trace("Adding empty column '" + val_field_ccb_name + "'")
    add_header_comment(val_field_ccb_name, 'Servant Keeper has no data for this field. Leaving it blank.')
    table = petl.addfield(table, val_field_ccb_name, '')
    return table


def add_fixed_string_column(table, val_field_ccb_name, fixed_string):
    assert isinstance(val_field_ccb_name, basestring)
    assert isinstance(fixed_string, basestring)
    trace("Adding fixed string column '" + val_field_ccb_name + "', with value '" + fixed_string + "'")
    add_header_comment(val_field_ccb_name, 'Servant Keeper has no data for this field. We are loading it ' \
        "with fixed value '" + fixed_string + "'.")
    table = petl.addfield(table, val_field_ccb_name, fixed_string)
    return table


def add_cloned_column(table, val_field_ccb_name, val_field_sk_name):
    assert isinstance(val_field_ccb_name, basestring)
    assert isinstance(val_field_sk_name, basestring)
    trace("Adding cloned column '" + val_field_ccb_name + "', from column '" + val_field_sk_name + "'")
    add_header_comment(val_field_ccb_name, "This field is cloned from Servant Keeper's '" + val_field_sk_name + \
        "' column.")
    table = petl.addfield(table, val_field_ccb_name, lambda rec: rec[val_field_sk_name])
    return table


def wrapped_converter_method(converter_method, sk_col_name=None, ccb_col_name=None):
    return lambda v, rec: converter_method(v, rec, sk_col_name, ccb_col_name)


def add_empty_column_then_convert(table, val_field_ccb_name, val_field_converter_method):
    assert isinstance(val_field_ccb_name, basestring)
    assert callable(val_field_converter_method)
    trace("Adding empty column '" + val_field_ccb_name + "', and then converting")
    add_header_comment(val_field_ccb_name, val_field_converter_method.__doc__)
    table = petl.addfield(table, val_field_ccb_name, '')
    table = petl.convert(table, val_field_ccb_name, wrapped_converter_method(val_field_converter_method,
        sk_col_name=None, ccb_col_name=val_field_ccb_name), pass_row=True, failonerror=True)
    return table


def add_cloned_column_then_convert(table, val_field_ccb_name, val_field_sk_name, val_field_converter_method):
    assert isinstance(val_field_ccb_name, basestring)
    assert isinstance(val_field_sk_name, basestring)
    assert callable(val_field_converter_method)
    trace("Adding cloned column '" + val_field_ccb_name + "', from column '" + val_field_sk_name + \
        "', and then converting")
    add_header_comment(val_field_ccb_name,
        "This field is sourced from Servant Keeper's '" + val_field_sk_name + "' column.")
    add_header_comment(val_field_ccb_name, val_field_converter_method.__doc__)
    table = petl.addfield(table, val_field_ccb_name, lambda rec: rec[val_field_sk_name])
    table = petl.convert(table, val_field_ccb_name, wrapped_converter_method(val_field_converter_method,
        sk_col_name=val_field_sk_name, ccb_col_name=val_field_ccb_name), pass_row=True, failonerror=True)
    return table


if __name__ == "__main__":
    main(sys.argv[1:])
