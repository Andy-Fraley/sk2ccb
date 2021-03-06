#!/usr/bin/env python


import sys, os.path, csv, argparse, petl, re, datetime, shutil, tempfile


# Fake class only for purpose of limiting global namespace to the 'g' object
class g:
    args = None
    xref_member_fields = None
    xref_w2s_skills_sgifts = None
    hitmiss_counters = None
    semicolon_sep_fields = None
    header_comments = None
    conversion_traces = None
    conversion_row_num = None
    start_conversion_time = None
    total_rows = None
    dict_family_id_counts = None
    xref_mailing_activities = None
    conversion_issue_notes = None


def main(argv):

    global g

    parser = argparse.ArgumentParser()
    parser.add_argument("--individuals-filename", required=True, help="Input UTF8 CSV with individuals data "
        "dumped from Servant Keeper")
    parser.add_argument("--families-filename", required=True, help="Input UTF8 CSV with families data ('Family "
        "Mailing Lists') dumped from Servant Keeper")
    parser.add_argument("--output-filename", required=True, help="Output CSV filename which will be loaded with "
        "individuals data in CCB import format ")
    parser.add_argument("--column-comments-filename", required=True, help="Output TEXT filename which will be loaded "
        "with per-column descriptive text summarizing how that column was transformed")
    parser.add_argument('--trace', action='store_true', help="If specified, prints to stdout as new columns are "
        "added")
    g.args = parser.parse_args()

    if not os.path.isfile(g.args.individuals_filename):
        print >> sys.stderr, "Error: cannot open file '" + g.args.individuals_filename + "'"
        sys.exit(1)

    table = petl.fromcsv(g.args.individuals_filename)

    # CAREFUL about interpreting joined 'Family Mailing Lists' field as should only count if associated with
    # a 'Primary Contact' individual which is not determined until later when convert_family_position() is
    # triggered
    table_families = petl.fromcsv(g.args.families_filename)
    table = petl.leftjoin(table, table_families, 'Family ID')

    # Rename the first and second 'General Notes' columns to be 'Family Notes' and 'Individual Notes' respectively
    header_row = petl.header(table)
    gen_notes_column_indices = [x for x in range(len(header_row)) if header_row[x] == 'General Notes']
    table = petl.rename(table, {
        gen_notes_column_indices[0]: 'Family Notes',
        gen_notes_column_indices[1]: 'Individual Notes',
        'Family ID': 'SK Family ID',
        'Individual ID': 'SK Individual ID',
        'First Name': 'SK First Name',
        'Middle Name': 'SK Middle Name',
        'Last Name': 'SK Last Name',
        'Suffix': 'SK Suffix',
        'City': 'SK City',
        'State': 'SK State',
        'Country': 'SK Country',
        'Home Phone': 'SK Home Phone',
        'Work Phone': 'SK Work Phone',
        'Cell Phone': 'SK Cell Phone',
        'Spiritual Gifts': 'SK Spiritual Gifts',
        'Gender': 'SK Gender',
        'Marital Status': 'SK Marital Status',
        'Baptized': 'SK Baptized',
        'Confirmed Date': 'SK Confirmed Date',
        'Confirmed': 'SK Confirmed',
        'Photo Release': 'SK Photo Release',
        'Church Transferred From': 'SK Church Transferred From',
        'Church Transferred To': 'SK Church Transferred To'
    })

    # Do the xref mappings specified in 'XRef-Member Status' tab of mapping spreadsheet
    g.xref_member_fields = get_xref_member_fields()

    # Do xref mappings specified in 'XRef-W2S, Skills, SGifts' tab of mapping spreadsheet
    g.xref_w2s_skills_sgifts = get_xref_w2s_skills_sgifts()
    g.semicolon_sep_fields = {}
    init_hitmiss_counters(g.xref_w2s_skills_sgifts)
    gather_semicolon_sep_field(g.semicolon_sep_fields, table, 'Willing to Serve')
    gather_semicolon_sep_field(g.semicolon_sep_fields, table, 'Skills')
    gather_semicolon_sep_field(g.semicolon_sep_fields, table, 'SK Spiritual Gifts')
    gather_semicolon_sep_field(g.semicolon_sep_fields, table, 'Mailing Lists')
    gather_semicolon_sep_field(g.semicolon_sep_fields, table, 'Family Mailing Lists', primary_contact_only=True)

    g.dict_family_id_counts = petl.valuecounter(table, 'SK Family ID')

    # print hitmiss_counters
    # for sk_field in hitmiss_counters:
    #    for item in hitmiss_counters[sk_field]:
    #        print >> sys.stderr, sk_field + ';' + item + ';' + str(hitmiss_counters[sk_field][item])

    trace('SETTING UP COLUMNS FOR CONVERSION...', banner=True)

    table = setup_column_conversions(table)

    trace('BEGINNING CONVERSION, THEN EMITTING TO CSV FILE...', banner=True)

    table.progress(200).tocsv(g.args.output_filename)

    trace('OUTPUT TO CSV COMPLETE.', banner=True)

    trace('WRITING HEADER COMMENTS TO SEPARATE FILE...', banner=True)

    write_column_comments_to_file(g.args.column_comments_filename)

    trace('DONE!', banner=True)


def write_column_comments_to_file(filename):
    sep = ''
    column_names = [x[0] for x in get_field_mappings()]
    with open(filename, 'wb') as column_comments_file:
        for column_name in column_names:
            column_comments_file.write(sep + "*** OUTPUT CCB COLUMN: '" + column_name + "'\n\n" + \
                                       g.header_comments[column_name].strip())
            sep = '\n\n\n'


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

def gather_semicolon_sep_field(semicolon_sep_fields, table, field_name, primary_contact_only=False):
    global g

    assert field_name in g.xref_w2s_skills_sgifts, '*** Unknown Servant Keeper field: ' + field_name + '. Aborting...'
    non_blank_rows = petl.selectisnot(table, field_name, u'')
    for indiv_id2semi_sep in petl.values(non_blank_rows, 'SK Individual ID', field_name):
        individual_id = indiv_id2semi_sep[0]
        list_skills_gifts = [x.strip() for x in indiv_id2semi_sep[1].split(';')]
        for skill_gift in list_skills_gifts:
            if skill_gift in g.xref_w2s_skills_sgifts[field_name]:
                ccb_area = g.xref_w2s_skills_sgifts[field_name][skill_gift][0]
                ccb_flag_to_set = g.xref_w2s_skills_sgifts[field_name][skill_gift][1]
                if not individual_id in g.semicolon_sep_fields:
                    semicolon_sep_fields[individual_id] = {
                        'Spiritual Gifts': [set(), set()],
                        'Passions': [set(), set()],
                        'Abilities': [set(), set()]
                    }
                add_at_offset = 0
                if primary_contact_only:
                    add_at_offset = 1
                g.semicolon_sep_fields[individual_id][ccb_area][add_at_offset].add(ccb_flag_to_set)
                # NOTE:  TODO, hitmiss accounting will be screwed up by family-level (Primary Contact Only) fields
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
            'Acts of God Drama Ministry': ('Passions', 'Activity: Drama'),
            'Bake or Prepare Food': ('Abilities', 'Skill: Cooking/Baking'),
            'Choir': ('Abilities', 'Arts: Vocalist'),
            'Faith Place': ('Passions', 'People: Children'),
            'High-School Small-Group Facilitator': ('Passions', 'People: Young Adults'),
            'High-School Youth Group Ldr/Chaperone': ('Passions', 'People: Young Adults'),
            'Kids Zone': ('Passions', 'People: Children'),
            'Liturgical Dance Ministry': ('Abilities', 'Arts: Dance'),
            'Middle-School Small-Group Facilitator': ('Passions', 'People: Children'),
            'Middle-School Youth Group Ldr/Chaperone': ('Passions', 'People: Children'),
            'Nursery Helper': ('Passions', 'People: Infants/Toddlers'),
            'Outreach - International - Mission trip': ('Passions', 'Activity: Global Missions'),
            'Outreach - Local - for adults': ('Passions', 'Activity: Local Outreach'),
            'Outreach - Local - for familiies/children': ('Passions', 'Activity: Local Outreach'),
            'Outreach - Local - Mission trip': ('Passions', 'Activity: Local Outreach'),
            'Outreach - U.S. - Mission trip': ('Passions', 'Activity: Regional Outreach'),
            'Vacation Bible School': ('Passions', 'People: Children'),
            'Visit home-bound individuals': ('Passions', 'People: Seniors')
        },
        'Skills':
        {
            'Compassion / Listening Skills': ('Abilities', 'Skill: Counseling'),
            'Cooking / Baking': ('Abilities', 'Skill: Cooking/Baking'),
            'Dancer / Choreographer': ('Abilities', 'Arts: Dance'),
            'Drama': ('Passions', 'Activity: Drama'),
            'Encouragement': ('Spiritual Gifts', 'Encouragement'),
            'Gardening / Yard Work': ('Abilities', 'Skill: Gardening'),
            'Giving': ('Spiritual Gifts', 'Giving'),
            'Information Technology': ('Abilities', 'Skill: Tech/Computers'),
            'Mailing Preparation': ('Abilities', 'Skill: Office Admin'),
            'Organizational Skills': ('Abilities', 'Skill: Office Admin'),
            'Photography / Videography': ('Abilities', 'Arts: Video/Photography'),
            'Prayer': ('Spiritual Gifts', 'Intercession'),
            'Sew / Knit / Crochet': ('Abilities', 'Arts: Sew/Knit/Crochet'),
            'Singer': ('Abilities', 'Arts: Vocalist'),
            'Teacher': ('Abilities', 'Skill: Education'),
            'Writer': ('Abilities', 'Arts: Writer')
        },
        'SK Spiritual Gifts':
        {
            'Administration': ('Spiritual Gifts', 'Administration'),
            'Apostleship': ('Spiritual Gifts', 'Apostleship'),
            'Craftsmanship': ('Spiritual Gifts', 'Craftsmanship'),
            'Discernment': ('Spiritual Gifts', 'Discernment'),
            'Encouragement': ('Spiritual Gifts', 'Encouragement'),
            'Evangelism': ('Spiritual Gifts', 'Evangelism'),
            'Faith': ('Spiritual Gifts', 'Faith'),
            'Giving': ('Spiritual Gifts', 'Giving'),
            'Helps': ('Spiritual Gifts', 'Helps'),
            'Hospitality': ('Spiritual Gifts', 'Hospitality'),
            'Intercession': ('Spiritual Gifts', 'Intercession'),
            'Word of Knowledge': ('Spiritual Gifts', 'Knowledge'),
            'Leadership': ('Spiritual Gifts', 'Leadership'),
            'Mercy': ('Spiritual Gifts', 'Mercy'),
            'Prophecy': ('Spiritual Gifts', 'Prophecy'),
            'Teaching': ('Spiritual Gifts', 'Teaching'),
            'Word of Wisdom': ('Spiritual Gifts', 'Wisdom')
        },
        'Mailing Lists':
        {
            'Golf Outing': ('Abilities', 'Sports: Golf'),
            '2015 Golf Outing': ('Abilities', 'Sports: Golf')
        },
        'Family Mailing Lists':
        {
            'Golf Outing': ('Abilities', 'Sports: Golf'),
            '2015 Golf Outing': ('Abilities', 'Sports: Golf')
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
# 'XRef-Member Status' mapping behaviors declaration
#######################################################################################################################

def get_xref_member_fields():
    xref_member_fields = {
        'Active Member': {
            'Membership Type': 'Member - Active',
            'Inactive/Remove': 'No',
            'Membership Date': get_date_joined,
            'Reason Left': '',
            'Membership Stop Date': '',
            'Deceased': ''
        },
        'Inactive Member': {
            'Membership Type': 'Member - Inactive',
            'Inactive/Remove': 'No',
            'Membership Date': get_date_joined,
            'Reason Left': '',
            'Membership Stop Date': '',
            'Deceased': ''
        },
        'Regular Attendee': {
            'Membership Type': 'Regular Attendee',
            'Inactive/Remove': 'No',
            'Membership Date': '',
            'Reason Left': '',
            'Membership Stop Date': '',
            'Deceased': ''
        },
        'Visitor': {
            'Membership Type': 'Guest',
            'Inactive/Remove': 'No',
            'Membership Date': '',
            'Reason Left': '',
            'Membership Stop Date': '',
            'Deceased': ''
        },
        'Non-Member': {
            'Membership Type': get_sourced_donor_or_biz,
            'Inactive/Remove': 'No',
            'Membership Date': '',
            'Reason Left': '',
            'Membership Stop Date': '',
            'Deceased': ''
        },
        'Pastor': {
            'Membership Type': 'Pastor',
            'Inactive/Remove': 'No',
            'Membership Date': '',
            'Reason Left': '',
            'Membership Stop Date': '',
            'Deceased': ''
        },
        'Deceased - Member': {
            'Membership Type': 'Member - Inactive',
            'Inactive/Remove': 'Yes',
            'Membership Date': get_date_joined,
            'Reason Left': 'Deceased',
            'Membership Stop Date': '',
            'Deceased': get_date_of_death
        },
        'Deceased - Non-Member': {
            'Membership Type': 'Friend',
            'Inactive/Remove': 'Yes',
            'Membership Date': '',
            'Reason Left': '',
            'Membership Stop Date': '',
            'Deceased': get_date_of_death
        },
        'None': {
            'Membership Type': '',
            'Inactive/Remove': 'Yes',
            'Membership Date': '',
            'Reason Left': '',
            'Membership Stop Date': '',
            'Deceased': ''
        },
        'No Longer Attend': {
            'Membership Type': 'Friend',
            'Inactive/Remove': 'No',
            'Membership Date': '',
            'Reason Left': 'No Longer Attend',
            'Membership Stop Date': '',
            'Deceased': ''
        },
        'Transferred out to other UMC': {
            'Membership Type': 'Friend',
            'Inactive/Remove': 'Yes',
            'Membership Date': get_date_joined,
            'Reason Left': 'Transferred Out to Other UMC',
            'Membership Stop Date': get_trf_out_date,
            'Deceased': ''
        },
        'Transferred out to Non UMC': {
            'Membership Type': 'Friend',
            'Inactive/Remove': 'Yes',
            'Membership Date': get_date_joined,
            'Reason Left': 'Transferred Out to Non UMC',
            'Membership Stop Date': get_trf_out_date,
            'Deceased': ''
        },
        'Withdrawal': {
            'Membership Type': 'Friend',
            'Inactive/Remove': 'No',
            'Membership Date': get_date_joined,
            'Reason Left': 'Withdrawal',
            'Membership Stop Date': get_trf_out_date,
            'Deceased': ''
        },
        'Charge Conf. Removal': {
            'Membership Type': 'Friend',
            'Inactive/Remove': 'Yes',
            'Membership Date': get_date_joined,
            'Reason Left': 'Charge Conference Removal',
            'Membership Stop Date': get_trf_out_date,
            'Deceased': ''
        },
        'Archives (Red Book)': {
            'Membership Type': '',
            'Inactive/Remove': 'Yes',
            'Membership Date': '',
            'Reason Left': 'Archives (Red Book)',
            'Membership Stop Date': '',
            'Deceased': ''
        }
    }
    return xref_member_fields


#######################################################################################################################
# 'XRef-Member Status' row getter utilities
#######################################################################################################################

def get_sourced_donor_or_biz(row):
    if row['Relationship'] == 'Organization Record':
        return 'Business'
    elif row['How Sourced?'][:8] == 'Donation':
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
    indiv_id = row['SK Individual ID']
    if indiv_id not in g.conversion_traces:
        g.conversion_traces[indiv_id] = []
    member_str = "Member '" + row['SK Last Name'] + ", " + row['SK First Name']
    if row['SK Middle Name'] != '':
        member_str += " " + row['SK Middle Name']
    member_str += "' (" + row['SK Individual ID'] + "). "
    if sk_col_name is not None:
        prefix_str = "Mapping from SK column '" + sk_col_name + "' to CCB column '" + \
            ccb_col_name + "'. "
    else:
        prefix_str = ''
    g.conversion_traces[indiv_id].append(prefix_str + msg_str)


def conversion_using_dict_map(row, value, sk_col_name, ccb_col_name, convert_dict, other, trace_other=False):
    if value in convert_dict:
        return convert_dict[value]
    elif other is not None:
        if trace_other and other:
            conversion_trace(row, "'" + value + "' is not a valid '" + ccb_col_name + "', so set to '" + other + "'.",
                 sk_col_name, ccb_col_name)
        return other
    else:
        raise KeyError(value + ' not in ' + str(convert_dict) + '.')


def is_phone_valid(phone_string):
    regex_phone = r'^\d{3}\-\d{3}\-\d{4}$'
    match = re.search(regex_phone, phone_string)
    if match is not None:
        return True
    else:
        return False


def xref_member_field_value(row, field_str):
    global g
    assert row['Member Status'] in g.xref_member_fields, "In xref_member_field_values, 'Member Status' of '" + \
        row['Member Status'] + "' is not valid key.  Aborting..."
    new_value = g.xref_member_fields[row['Member Status']][field_str]
    if callable(new_value):
        new_value = new_value(row)
    return new_value


def xref_w2s_gather(row, gather_str):
    # NOTE: This method counts on all convert_family_position() calls happening to set up 'Primary Contact' *before*
    # this method is called
    global g
    return_set = set()
    indiv_id = row['SK Individual ID']
    if indiv_id in g.semicolon_sep_fields:
        for elem in g.semicolon_sep_fields[indiv_id][gather_str][0]:
            return_set.add(elem)
        if row['Family Position'] == 'Primary Contact':
            for elem in g.semicolon_sep_fields[indiv_id][gather_str][1]:
                return_set.add(elem)
        return ';'.join(return_set)
    else:
        return ''


def is_only_family_member(row):
    global g
    assert row['SK Family ID'] != '', row_info_and_msg(row, "Row has blank 'SK Family ID'.")
    return g.dict_family_id_counts[row['SK Family ID']] == 1


def row_info_and_msg(row, msg_str):
    row_info_str = row['SK First Name'] + ' ' + row['SK Last Name'] + ' (' + row['SK Individual ID'] + ')'
    return row_info_str + '. ' + msg_str


def date_format(date):
    return str(date.year) + '-' + str(date.month) + '-' + str(date.day)


def add_invalid_sk_field_contents_to_notes(row, value, sk_col_name):
    global g
    add_conversion_note(row['SK Individual ID'], "Servant Keeper field '" + sk_col_name + "' had value '" + \
        value + "' which could not be loaded into CCB.")


def add_conversion_note(sk_indiv_id, note_str):
    global g
    append_indexed_dict_string(sk_indiv_id, g.conversion_issue_notes, note_str)


def append_indexed_dict_string(index, indexed_dict, append_str):
    if not index in indexed_dict:
        indexed_dict[index] = append_str
    else:
        indexed_dict[index] += '\n\n' + append_str


#######################################################################################################################
# Field converter methods (convert_xyz)
#######################################################################################################################

def convert_date(value, row, sk_col_name, ccb_col_name):
    """If this field is of exact format 'm/d/yyyy', and 'm', 'd', and 'yyyy' represent a valid date, it is retained,
    else it is set to blank ('')."""

    try:
        date = datetime.datetime.strptime(value.strip(), '%m/%d/%Y')
        new_value = date_format(date)
    except ValueError:
        new_value = ''
    except:
        raise
    if new_value == '' and not re.match(r'(\s+/\s+/\s+)|(^$)', value):
        add_invalid_sk_field_contents_to_notes(row, value, sk_col_name)
        conversion_trace(row, "Blanked invalid date: '" + value + "'", sk_col_name, ccb_col_name)
    return new_value


def convert_phone(value, row, sk_col_name, ccb_col_name):
    """If this field is of exact format 'nnn-nnn-nnnn', it is retained, else it is set to blank ('')."""

    if is_phone_valid(value):
        new_value = value
    else:
        new_value = ''
        if not re.match(r'\s+\-\s+\-\s+', value):
            add_invalid_sk_field_contents_to_notes(row, value, sk_col_name)
            conversion_trace(row, "Blanked invalid phone number: '" + value + "'", sk_col_name, ccb_col_name)
    return new_value


def convert_family_position(value, row, sk_col_name, ccb_col_name):
    """This field is remapped as follows:
        'Head of Household' -> 'Primary Contact',
        'Spouse' -> 'Spouse',
        'Son' -> 'Child',
        'Daughter' -> 'Child',
        'Child' -> 'Child',
        'Organization Record' -> 'Primary Contact' (and 'Membership Type' is set to 'Business')
        <anything_else> -> 'Other'."""

    convert_dict = {
        'Head of Household': 'Primary Contact',
        'Spouse': 'Spouse',
        'Son': 'Child',
        'Daughter': 'Child',
        'Child': 'Child',
        'Organization Record': 'Primary Contact'
    }
    new_value = conversion_using_dict_map(row, value, sk_col_name, ccb_col_name, convert_dict, 'Other',
        trace_other=True)
    # TODO - Un-comment this when get new data from Carol
    #assert new_value == 'Primary Contact' or not is_only_family_member(row), row_info_and_msg(row, "A one-member " \
    #    "family has a member who is not 'Primary Contact'.  This should NEVER occur.  Aborting...")
    if new_value != 'Primary Contact' and is_only_family_member(row):
        conversion_trace(row, "'" + new_value + "' changed to 'Primary Contact', since only member of Family ID '" + \
            str(row['SK Family ID']) + "'", sk_col_name, ccb_col_name)
        new_value = 'Primary Contact'
    return new_value


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


def convert_photo_release(value, row, sk_col_name, ccb_col_name):
    """Change to Title Case for one value that is not Title Case.  'Granted, but name release denied' ->
    'Granted, But Name Release Denied')."""

    if value == 'Granted, but name release denied':
        return 'Granted (Name Release Denied)'
    else:
        return value


def convert_ethnicity(value, row, sk_col_name, ccb_col_name):
    """Change to Title Case for one value that is not Title Case.  'Multi racial' -> 'Multi Racial'."""

    if value == 'Multi racial':
        return 'Multi Racial'
    else:
        return value


def convert_limited_access_user(value, row, sk_col_name, ccb_col_name):
    """By setting to 'No', we intend all users to be 'Basic User'."""

    return 'No'


def convert_listed(value, row, sk_col_name, ccb_col_name):
    """Children ('family position' == 'Child') with blank 'confirmed date' and blank 'birthday' will be made
    'Listed'='No'.  Children with valid 'confirmed date' or valid 'birthday' will be made 'Listed'='Yes'."""

    assert not (row['Confirmed Date'] != '' and row['Confirmed'] == 'No'), row_info_and_msg(row,
        "Row has valid 'Confirmed Date' but indicates 'Confirmed' == 'No'.")

    if (row['Family Position'] == 'Child' or row['Family Position'] == 'Other') and row['Confirmed Date'] == '' and \
       row['Confirmed'] != 'Yes' and row['Birthday'] == '':
        new_value = 'No'
        if row['Family Position'] == 'Other':
            conversion_trace(row, "Not enough info to conclude person's age/confirmation, so setting 'Listed'='No'.",
                sk_col_name, ccb_col_name)
            add_conversion_note(row['SK Individual ID'], "Not enough info to conclude person's age/confirmation, " \
                "so setting 'Listed'='No'.")
    else:
        new_value = 'Yes'
    return new_value


def convert_contact_phone(value, row, sk_col_name, ccb_col_name):
    """This field is loaded with 'home phone' value if it's a valid phone number, else 'cell phone' if that's valid,
    and if neither 'home phone' nor 'cell phone' are valid, then this field is blank"""

    home_phone_valid = is_phone_valid(row['SK Home Phone'])
    cell_phone_valid = is_phone_valid(row['SK Cell Phone'])
    if home_phone_valid:
        return row['SK Home Phone']
    elif cell_phone_valid:
        return row['SK Cell Phone']
    else:
        return ''


def convert_membership_date(value, row, sk_col_name, ccb_col_name):
    """If person was *ever* a member current or prior (i.e. Servant Keeper's 'Member Status' is one of:
    'Active Member', 'Inactive Member', 'Deceased - Member', 'Transferred out to other UMC',
    'Transferred out to Non UMC', 'Withdrawal', 'Charge Conf. Removal'), and Servant Keeper's 'Date Joined' field
    is a valid date, then this date is set Servant Keeper's 'Date Joined', else it is set to blank ('')"""

    new_value = xref_member_field_value(row, 'Membership Date')
    return convert_date(new_value, row, sk_col_name, ccb_col_name)


def convert_membership_stop_date(value, row, sk_col_name, ccb_col_name):
    """If person was a prior member (i.e. Servant Keeper's 'Member Status' is one of: 'Transferred out to other UMC',
    'Transferred out to Non UMC', 'Withdrawal', 'Charge Conf. Removal'), and Servant Keeper's
    'Trf out/Withdrawal Date' field is a valid date, then this date is set to Servant Keeper's
    'Trf out/Withdrawal Date', else it is set to blank ('')"""

    new_value = xref_member_field_value(row, 'Membership Stop Date')
    return convert_date(new_value, row, sk_col_name, ccb_col_name)


def convert_membership_type(value, row, sk_col_name, ccb_col_name):
    """This field has a complex mapping based on Servant Keeper 'Member Status' (and 'How Sourced?') fields as follows:
        'Active Member' -> 'Member - Active',
        'Inactive Member' -> 'Member - Inactive',
        'Regular Attendee' -> 'Regular Attendee',
        'Visitor' -> 'Guest',
        'Non-Member ('How Sourced?' <> 'Donation...')' -> 'Friend',
        'Non-Member ('How Sourced?' == 'Donation...')' -> 'Donor',
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
    assert row['Member Status'] in g.xref_member_fields, "In convert_membership_type(), 'Member Status' of '" + \
        row['Member Status'] + "' is not valid key.  Aborting..."
    new_value = g.xref_member_fields[row['Member Status']]['Membership Type']
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
    """If Servant Keeper's 'Active Profile' is not 'Yes', then this CCB field, 'Inactive/Remove' is set to 'Yes', so
    the CCB record is removed.  Else, this field has a complex mapping based on Servant Keeper 'Member Status'
    (and 'How Sourced?') fields as follows:
        'Active Member' -> blank ('', i.e. active so retain),
        'Inactive Member' -> blank ('', i.e. active so retain),
        'Regular Attendee' -> blank ('', i.e. active so retain),
        'Visitor' -> blank ('', i.e. active so retain),
        'Non-Member ('How Sourced?' <> 'Donation...')' -> blank ('', i.e. active so retain),
        'Non-Member ('How Sourced?' == 'Donation...')' -> blank ('', i.e. active so retain),
        'Pastor' -> blank ('', i.e. active so retain),
        'Deceased - Member' -> 'Yes' (i.e. inactive so remove),
        'Deceased - Non-Member' -> 'Yes' (i.e. inactive so remove),
        'None' -> 'Yes' (i.e. inactive so remove),
        'No Longer Attend' -> blank ('', i.e. active so retain),
        'Transferred out to other UMC' -> 'Yes' (i.e. inactive so remove),
        'Transferred out to Non UMC' -> 'Yes' (i.e. inactive so remove),
        'Withdrawal' -> blank ('', i.e. active so retain)...AndyF comment - shouldn't this become remove/inactive???,
        'Charge Conf. Removal' -> 'Yes' (i.e. inactive so remove),
        'Archives (Red Book)' -> 'Yes' (i.e. inactive so remove)."""

    global g
    assert row['Member Status'] in g.xref_member_fields, "In convert_inactive_remove(), 'Member Status' of '" + \
        row['Member Status'] + "' (SK Individual ID " + row['SK Individual ID'] + ") is not valid key.  Aborting..."
    new_value = g.xref_member_fields[row['Member Status']]['Inactive/Remove']
    if new_value == 'No' and row['Active Profile'] == 'No':
        new_value = 'Yes'  # (Remove)
        conversion_trace(row, "SK 'Active Profile' is 'No', so marking this as 'Inactive/Remove'='Yes' in CCB even " \
            "though it'd be 'No' based solely on mapping of SK 'Member Status'", sk_col_name, ccb_col_name)
        add_conversion_note(row['SK Individual ID'], "SK 'Active Profile' is 'No', so marking this as " \
            "'Inactive/Remove'='Yes' in CCB even though it'd be 'No' based solely on mapping of SK 'Member Status'")
    return new_value


def convert_notes(value, row, sk_col_name, ccb_col_name):
    """This field is formed from both 'Family Notes' (1st 'General Notes') and 'Individual Notes' (2nd
    'General Notes') and 'Family Relationship' fields from Servant Keeper.  It is pre-pended by language
    indicating it's from Servant Keeper 'General Notes' and with a date-time stamp of the time that
    transform utility was run. The separate notes sections are pre-pended with 'FAMILY NOTES:' (if present
    and if this individual is 'Primary Contact') and 'INDIVIDUAL NOTES:' (if present) and
    'FAMILY RELATIONSHIP NOTES:' (if present)."""

    global g
    family_notes_str = None
    individual_notes_str = None
    family_relationship_notes_str = None
    conversion_notes_str = None

    # Note - For look-up below to work, the 'family position' field MUST be convert()'d prior to this
    # 'notes' field
    if row['Family Position'] == 'Primary Contact' and row['Family Notes']:
        family_notes_str = '\n\nSERVANT KEEPER - FAMILY NOTES:\n\n' + row['Family Notes']

    if row['Individual Notes']:
        individual_notes_str = '\n\nSERVANT KEEPER - INDIVIDUAL NOTES:\n\n' + row['Individual Notes']

    if row['Family Relationship']:
        family_relationship_notes_str = '\n\nSERVANT KEEPER - FAMILY RELATIONSHIP NOTES:\n\n' + \
            row['Family Relationship']

    # Note - For look-up below to work, this convert() must run after ALL convert_date() and convert_phone()
    # conversions
    if row['SK Individual ID'] in g.conversion_issue_notes:
        conversion_notes_str = '\n\nSERVANT KEEPER -> CCB CONVERSION ISSUES:\n\n' + \
            g.conversion_issue_notes[row['SK Individual ID']]

    if family_notes_str or individual_notes_str or family_relationship_notes_str or conversion_notes_str:
        output_str = 'THESE NOTES ARE FROM SERVANT KEEPER CONVERSION ({})'.format(
            datetime.datetime.now().strftime('%Y-%m-%d %H:%M'))
        if family_notes_str:
            output_str += family_notes_str
        if individual_notes_str:
            output_str += individual_notes_str
        if family_relationship_notes_str:
            output_str += family_relationship_notes_str
        if conversion_notes_str:
            output_str += conversion_notes_str
        return output_str
    else:
        return ''


def convert_how_they_heard(value, row, sk_col_name, ccb_col_name):
    """This field is remapped as follows:
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

    convert_dict = {
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
    }
    return conversion_using_dict_map(row, value, sk_col_name, ccb_col_name, convert_dict, '', trace_other=False)


def convert_how_they_joined(value, row, sk_col_name, ccb_col_name):
    """This field is remapped as follows:
        'Associate' -> 'Associate',
        'Confirmation' -> 'Confirmation',
        'Membership Restored' -> 'Membership Restored',
        'Profession of Faith' -> 'Profession of Faith',
        'Transferred  from other UMC' -> 'Transferred from Other UMC',
        'Transferred from Non UMC' -> 'Transferred from Non UMC',
        '' -> ''.
    Note:  the *only* remapping happening above is removal of extra space from 'Transferred  from other UMC'
    setting.  And to upper case 'Other'"""

    convert_dict = {
        'Associate': 'Associate',
        'Confirmation': 'Confirmation',
        'Membership Restored': 'Membership Restored',
        'Profession of Faith': 'Profession of Faith',
        'Transferred  from other UMC': 'Transferred from Other UMC',
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
    assert row['Member Status'] in g.xref_member_fields, "In convert_reason_left_church(), 'Member Status' of '" + \
        row['Member Status'] + "' is not valid key.  Aborting..."
    value = g.xref_member_fields[row['Member Status']]['Reason Left']
    return value


def convert_deceased(value, row, sk_col_name, ccb_col_name):
    """If person was a member or non-member who has died (i.e. Servant Keeper's 'Member Status' field is one of:
    'Deceased - Member', 'Deceased - Non-Member'), and Servant Keeper's 'Date of Death' field is a valid date,
    then this field is set to Servant Keeper's 'Date of Death' field, else it is set to blank ('')."""

    new_value = xref_member_field_value(row, 'Deceased')
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

    return xref_w2s_gather(row, 'Spiritual Gifts')


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

    return xref_w2s_gather(row, 'Passions')


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

    return xref_w2s_gather(row, 'Abilities')


def convert_burial_information(value, row, sk_col_name, ccb_col_name):
    """This field contains formatted burial information that is to be placed in a Note associated with the
    'Death' process 'Record Burial Information' queue."""
    new_value = ''
    sep = 'BURIAL INFORMATION (FROM SERVANT KEEPER)\n\n'
    burial_date = convert_date(row['Burial: Date'], row, 'Burial: Date', ccb_col_name)
    if burial_date != '':
        burial_date_obj = datetime.datetime.strptime(burial_date, '%Y-%m-%d')
        burial_date_str = str(burial_date_obj.month) + '/' + str(burial_date_obj.day) + '/' + str(burial_date_obj.year)
        new_value += sep + 'Burial Date: ' + burial_date_str
        sep = '\n'
    if row['Burial: Officating Pastor'].strip() != '':
        new_value += sep + 'Burial Officiating Pastor: ' + row['Burial: Officating Pastor'].strip()
        sep = '\n'
    if row['Burial: Site Title'].strip() != '':
        new_value += sep + 'Burial Site Title: ' + row['Burial: Site Title'].strip()
        sep = '\n'
    if row['Burial: City, County, St'].strip() != '':
        new_value += sep + 'Burial City, County, State: ' + row['Burial: City, County, St'].strip()
        sep = '\n'
    return new_value


def convert_baptism_information(value, row, sk_col_name, ccb_col_name):
    """This field contains formatted baptism information that is to be placed in a Note associated with the
    'Baptism' process 'Record Baptism Information' queue."""
    new_value = ''
    sep = 'BAPTISM INFORMATION (FROM SERVANT KEEPER)\n\n'
    if row['Place of Birth'].strip() != '':
        new_value += sep + 'Place of Birth: ' + row['Place of Birth'].strip()
        sep = '\n'
    return new_value


def convert_spirit_mailing(value, row, sk_col_name, ccb_col_name):
    """This field is remapped as follows:
        'Yes' -> 'Postal Mail',
        'No' -> 'None'."""

    convert_dict = {
        'Yes': 'Postal Mail',
        'No': 'None'
    }
    return conversion_using_dict_map(row, value, sk_col_name, ccb_col_name, convert_dict, None)


#######################################################################################################################
# Core utility conversion setup method.
#######################################################################################################################

def setup_column_conversions(table):

    global g

    g.header_comments = {}
    g.conversion_traces = {}
    g.conversion_issue_notes = {}

    field_ccb_name = 0
    field_sk_name = 1
    field_converter_method = 2
    field_custom_or_process_queue = 3

    field_mappings = get_field_mappings()

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

    # TODO - Remove the reorder when Carol's extract is in right order
    # Put columns in better-to-read ordering to better allow for FREEZE WINDOW in Excel
    l = list(petl.header(table))
    l.remove('SK Last Name')
    l.remove('SK First Name')
    l.remove('Mailing Name')
    l.insert(0, 'Mailing Name')
    l.insert(0, 'SK First Name')
    l.insert(0, 'SK Last Name')
    table = petl.cut(table, l)

    return table


def get_field_mappings():
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
    field_mappings = [
        # Core (silver sample.xls) columns
        ['Family ID', 'SK Family ID'],
        ['Individual ID', 'SK Individual ID'],
        ['Family Position', 'Relationship', convert_family_position],
        ['Prefix', 'Title', convert_prefix],
        ['First Name', 'Preferred Name'],
        ['Middle Name', 'SK Middle Name'],
        ['Last Name', 'SK Last Name'],
        ['Suffix', 'SK Suffix', convert_suffix],
        ['Legal Name', 'SK First Name'],
        ['Inactive/Remove', None, convert_inactive_remove],
        ['Campus'],
        ['Email', 'Individual e-Mail'],
        ['Mailing Street', 'Address'],
        ['Mailing Street Line 2', 'Address Line 2'],
        ['City', 'SK City'],
        ['State', 'SK State'],
        ['Postal Code', 'Zip Code'],
        ['Country', 'SK Country', convert_country],
        ['Mailing Carrier Route'],
        ['Home Street', 'Address'],
        ['Home Street Line 2', 'Address Line 2'],
        ['Home City', 'SK City'],
        ['Home State', 'SK State'],
        ['Home Postal Code', 'Zip Code'],
        ['Area of Town'],
        ['Contact Phone', None, convert_contact_phone],
        ['Home Phone', 'SK Home Phone', convert_phone],
        ['Work Phone', 'SK Work Phone', convert_phone],
        ['Cell Phone', 'SK Cell Phone', convert_phone],
        ['Service Provider'],
        ['Fax'],
        ['Pager'],
        ['Emergency Phone'],
        ['Emergency Contact Name'],
        ['Birthday', 'Birth Date', convert_date],
        ['Anniversary', 'Wedding Date', convert_date],
        ['Gender', 'SK Gender'],
        ['Giving #', 'Env #'],
        ['Marital Status', 'SK Marital Status'],
        ['Membership Date', 'Date Joined', convert_membership_date],
        ['Membership Stop Date', 'Trf out/Withdrawal Date', convert_membership_stop_date],
        ['Membership Type', None, convert_membership_type],
        ['Baptized', 'SK Baptized'],
        ['School', 'School District'],
        ['School Grade'],
        ['Known Allergies'],
        ['Confirmed No Allergies'],
        ['Approved to Work with Children'],
        ['Approved to Work with Children Stop Date'],
        ['Commitment Date'],
        ['How They Heard', 'How Sourced?', convert_how_they_heard],
        ['How They Joined', 'How Joined', convert_how_they_joined],
        ['Reason Left Church', None, convert_reason_left_church],
        ['Job Title', 'Occupation'],
        ['Work Street 1'],
        ['Work Street 2'],
        ['Work City'],
        ['Work State'],
        ['Work Postal Code'],
        ['Current Story'],
        ['Commitment Story'],
        ['Deceased', 'Date of Death', convert_deceased],
        ['Facebook Username'],
        ['Twitter Username'],
        ['Blog Username'],
        ['Website My'],
        ['Website Work'],
        ['Military'],  # Anything from Carol?
        ['Spiritual Maturity'],
        ['Spiritual Gifts', None, convert_spiritual_gifts],
        ['Passions', None, convert_passions],
        ['Abilities/Skills', None, convert_abilities_skills],
        ['Church Services I Attend'],
        ['Personal Style'],

        # No such thing as 'other' address info in silver_sample file, but they're valid fields
        ['Other Street', 'Alt Address'],
        ['Other Street Line 2', 'Alt Address Line 2'],
        ['Other City', 'Alt City'],
        ['Other Country', 'Alt Country', convert_country],
        ['Other State', 'Alt State'],
        ['Other Postal Code', 'Alt Zip Code'],

        # Burial and Baptism process queue data
        ["PROCESS='Death' QUEUE='Record Burial Information'", None, convert_burial_information, 'process_queue'],
        ["PROCESS='Baptism' QUEUE='Record Baptism Information'", None, convert_baptism_information, 'process_queue'],

        # Custom fields
        ['Baptism Date', 'Baptized Date', convert_date, 'custom-date'],
        ['Baptized By', 'Baptized by', None, 'custom-text'],
        ['Confirmed Date', 'SK Confirmed Date', convert_date, 'custom-date'],
        ['Confirmed', 'SK Confirmed', None, 'custom-pulldown'],
        ['Mailbox Number', 'Mail Box #', None, 'custom-text'],
        ['Spirit Mailing', 'The Spirit Mailing', convert_spirit_mailing, 'custom-pulldown'],
        ['Photo Release', 'SK Photo Release', convert_photo_release, 'custom-pulldown'],
        ['Ethnicity', 'Racial/Ethnic identification', convert_ethnicity, 'custom-pulldown'],
        ['Transferred Frm', 'SK Church Transferred From', None, 'custom-text'],
        ['Transferred To', 'SK Church Transferred To', None, 'custom-text'],
        ['Pastr When Join', 'Pastor when joined', None, 'custom-text'],
        ['Pastr When Leav', 'Pastor when leaving', None, 'custom-text'],
        ['SK Indiv ID', 'SK Individual ID', None, 'custom-text'],

        # Putting these fields towards the end so that dependent 'birthday' and 'confirmed' fields can be stuffed
        # before
        ['Limited Access User', None, convert_limited_access_user],
        ['Listed', None, convert_listed],

        # Notes field last so it can accumulate notes about all invalid dates/phones in SK, and so it can rely
        # on 'Primary Contact' already having been set
        ['Notes', None, convert_notes]
    ]
    return field_mappings


def add_header_comment(val_field_ccb_name, header_str):
    global g
    if not header_str:
        return
    header_str = format_header_comment(header_str)
    append_indexed_dict_string(val_field_ccb_name, g.header_comments, header_str)


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
