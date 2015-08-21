#!/usr/bin/env python


import sys, getopt, os.path, csv, argparse, petl, re
from collections import namedtuple


def main(argv):
    global xref_member_fields
    global xref_how_sourced
    global xref_w2s_skills_sgifts
    global hitmiss_counters
    global semicolon_sep_fields
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--individuals-filename", required=True, help="Input CSV with individuals data dumped " \
                        "from Servant Keeper")
    parser.add_argument("--child-approvals-filename", required=True, help="Filename of CSV file listing approval " \
                        "dates that individuals got various clearances to work with children")
    parser.add_argument("--output-filename", required=True, help="Output CSV filename which will be loaded with " \
                        "individuals data in CCB import format ")
    args = parser.parse_args()

    if not os.path.isfile(args.individuals_filename):
        print >> sys.stderr, "Error: cannot open file '" + args.individuals_filename + "'"
        sys.exit(1)

    table_sk = petl.fromcsv(args.individuals_filename)

    # Drop out all rows in Servant Keeper marked as 'Active Profile' != 'Yes' (i.e. == 'No')
    # table = petl.select(table, "{Active Profile} == 'Yes'")

    table_ccb = cut_and_rename_columns(table_sk)

    # Remove empty dates and dates missing year
    regex_empty_dates = r'^(\s+/\s+/\s+)|(\d{1,2}/\d{1,2}/\s+)'
    table_ccb = petl.sub(table_ccb, 'birthday', regex_empty_dates, '')
    table_ccb = petl.sub(table_ccb, 'deceased', regex_empty_dates, '')
    table_ccb = petl.sub(table_ccb, 'anniversary', regex_empty_dates, '')
    table_ccb = petl.sub(table_ccb, 'baptism date', regex_empty_dates, '')
    table_ccb = petl.sub(table_ccb, 'pq__burial date', regex_empty_dates, '')
    table_ccb = petl.sub(table_ccb, 'confirmed date', regex_empty_dates, '')
    table_ccb = petl.sub(table_ccb, 'membership date', regex_empty_dates, '')
    table_ccb = petl.sub(table_ccb, 'membership stop date', regex_empty_dates, '')
    table_ccb = petl.sub(table_ccb, 'pq__guest_followup 1 month', regex_empty_dates, '')
    table_ccb = petl.sub(table_ccb, 'pq__guest_followup 1 week', regex_empty_dates, '')
    table_ccb = petl.sub(table_ccb, 'pq__guest_followup 2 weeks', regex_empty_dates, '')

    # Remove empty phone numbers
    regex_empty_phones = r'^\s+\-\s+\-\s+$'
    table_ccb = petl.sub(table_ccb, 'cell phone', regex_empty_phones, '')
    table_ccb = petl.sub(table_ccb, 'home phone', regex_empty_phones, '')
    table_ccb = petl.sub(table_ccb, 'work phone', regex_empty_phones, '')

    # Clones
    # TODO, use 'index=' to place these new columns at right locations (using 'add_after' helper?)
    table_ccb = petl.addfield(table_ccb, 'sync id', lambda rec: rec['individual id'])
    table_ccb = petl.addfield(table_ccb, 'mailing street', lambda rec: rec['home street'])
    table_ccb = petl.addfield(table_ccb, 'mailing street line 2', lambda rec: rec['home street line 2'])
    table_ccb = petl.addfield(table_ccb, 'home_city', lambda rec: rec['city'])
    table_ccb = petl.addfield(table_ccb, 'home_state', lambda rec: rec['state'])
    table_ccb = petl.addfield(table_ccb, 'home_postal code', lambda rec: rec['postal code'])

    # Simple remaps
    table_ccb = petl.convert(table_ccb, 'inactive/remove', {'Yes': '', 'No': 'yes'})

    # Do the xref mappings specified in 'XRef-Member Status' tab of mapping spreadsheet
    xref_member_fields = get_xref_member_fields()
    table_tmp = petl.addfield(table_sk, 'ccb__membership type', get_membership_type)
    table_tmp = petl.addfield(table_tmp, 'ccb__inactive/remove', get_inactive_remove)
    table_tmp = petl.addfield(table_tmp, 'ccb__membership date', get_membership_date)
    table_tmp = petl.addfield(table_tmp, 'ccb__reason left', get_reason_left)
    table_tmp = petl.addfield(table_tmp, 'ccb__membership stop date', get_membership_stop_date)
    table_tmp = petl.addfield(table_tmp, 'ccb__deceased', get_deceased)

    # Do single xref mapping specified in 'XRef-How Sourced' tab of mapping spreadsheet
    xref_how_sourced = get_xref_how_sourced()
    table_tmp = petl.addfield(table_tmp, 'ccb_how they heard', get_how_they_heard)

    # Do xref mappings specified in 'XRef-W2S, Skills, SGifts' tab of mapping spreadsheet
    xref_w2s_skills_sgifts = get_xref_w2s_skills_sgifts()
    semicolon_sep_fields = {}
    init_hitmiss_counters(xref_w2s_skills_sgifts)
    gather_semicolon_sep_field(semicolon_sep_fields, table_tmp, 'Willing to Serve')
    gather_semicolon_sep_field(semicolon_sep_fields, table_tmp, 'Skills')
    gather_semicolon_sep_field(semicolon_sep_fields, table_tmp, 'Spiritual Gifts')
    table_tmp = petl.addfield(table_tmp, 'ccb__passions', get_gathered_passions)
    table_tmp = petl.addfield(table_tmp, 'ccb__abilities', get_gathered_abilities)
    table_tmp = petl.addfield(table_tmp, 'ccb__spiritual_gifts', get_gathered_spiritual_gifts)

    # print semicolon_sep_fields

    # print hitmiss_counters
    # for sk_field in hitmiss_counters:
    #    for item in hitmiss_counters[sk_field]:
    #        print >> sys.stderr, sk_field + ';' + item + ';' + str(hitmiss_counters[sk_field][item])

    # petl.tocsv(table, args.output_filename)

    print table_ccb
    print table_tmp


#######################################################################################################################
# 'XRef-XRef-W2S, Skills, SGifts' semi-colon field gathering
#######################################################################################################################

def gather_semicolon_sep_field(semicolon_sep_fields, table, field_name):
    global xref_w2s_skills_sgifts

    if not field_name in xref_w2s_skills_sgifts:
        print >> sys.stderr, '*** Unknown Servant Keeper field: ' + field_name
        sys.exit(1)
    non_blank_rows = petl.selectisnot(table, field_name, u'')
    for indiv_id2semi_sep in petl.values(non_blank_rows, 'Individual ID', field_name):
        individual_id = indiv_id2semi_sep[0]
        list_skills_gifts = [x.strip() for x in indiv_id2semi_sep[1].split(';')]
        for skill_gift in list_skills_gifts:
            if skill_gift in xref_w2s_skills_sgifts[field_name]:
                ccb_area = xref_w2s_skills_sgifts[field_name][skill_gift][0]
                ccb_flag_to_set = xref_w2s_skills_sgifts[field_name][skill_gift][1]
                if not individual_id in semicolon_sep_fields:
                    semicolon_sep_fields[individual_id] = {
                        'spiritual gifts': set(),
                        'passions': set(),
                        'abilities': set()
                    }
                semicolon_sep_fields[individual_id][ccb_area].add(ccb_flag_to_set)
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
    global hitmiss_counters
    hitmiss_counters = {}
    for sk_field in xref_w2s_skills_sgifts_mappings:
        hitmiss_counters[sk_field] = {}
        for item in xref_w2s_skills_sgifts_mappings[sk_field]:
            hitmiss_counters[sk_field][item] = 0

def record_hitmiss(sk_field, item, count):
    global hitmiss_counters
    if not sk_field in hitmiss_counters:
        hitmiss_counters[sk_field] = {}
    if not item in hitmiss_counters[sk_field]:
        hitmiss_counters[sk_field][item] = 0
    hitmiss_counters[sk_field][item] += count


#######################################################################################################################
# 'XRef-XRef-W2S, Skills, SGifts' helper functions to add 'passions', 'abilities', and 'spiritual gifts' fields
#######################################################################################################################

def get_gathered_passions(row):
    global semicolon_sep_fields

    indiv_id = row['Individual ID']
    if indiv_id in semicolon_sep_fields:
        return ';'.join(semicolon_sep_fields[indiv_id]['passions'])
    else:
        return ''

def get_gathered_abilities(row):
    global semicolon_sep_fields

    indiv_id = row['Individual ID']
    if indiv_id in semicolon_sep_fields:
        return ';'.join(semicolon_sep_fields[indiv_id]['abilities'])
    else:
        return ''

def get_gathered_spiritual_gifts(row):
    global semicolon_sep_fields

    indiv_id = row['Individual ID']
    if indiv_id in semicolon_sep_fields:
        return ';'.join(semicolon_sep_fields[indiv_id]['spiritual gifts'])
    else:
        return ''


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
# 'XRef-How Sourced' getters
#######################################################################################################################

def get_how_they_heard(row):
    global xref_how_sourced

    value = xref_how_sourced[row['How Sourced?']]

    return value


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
# 'XRef-Member Status' getters
#######################################################################################################################

def get_membership_type(row):
    global xref_member_fields

    value = xref_member_fields[row['Member Status']]['membership type']
    if callable(value):
        value = value(row)

    return value


def get_inactive_remove(row):
    global xref_member_fields

    value = xref_member_fields[row['Member Status']]['inactive/remove']

    return value


def get_membership_date(row):
    global xref_member_fields

    value = xref_member_fields[row['Member Status']]['membership date']
    if callable(value):
        value = value(row)

    return value


def get_reason_left(row):
    global xref_member_fields

    value = xref_member_fields[row['Member Status']]['reason left']

    return value


def get_membership_stop_date(row):
    global xref_member_fields

    value = xref_member_fields[row['Member Status']]['membership stop date']
    if callable(value):
        value = value(row)

    return value


def get_deceased(row):
    global xref_member_fields

    value = xref_member_fields[row['Member Status']]['deceased']
    if callable(value):
        value = value(row)

    return value


#######################################################################################################################
# 'XRef-Member Status' row utilities
#######################################################################################################################

def get_sourced_donor(row):
    if row['How Sourced?'][:8] == 'Donation':
        return 'Donor'
    else:
        return 'Friend'


def get_date_joined(row):
    date_joined = row['Date Joined']
    date_joined = re.sub(r'^(\s+/\s+/\s+)|(\d{1,2}/\d{1,2}/\s+)', '', date_joined)  # Strip blank or invalid dates
    return date_joined


def get_trf_out_date(row):
    trf_out_date = row['Trf out/Withdrawal Date']
    trf_out_date = re.sub(r'^(\s+/\s+/\s+)|(\d{1,2}/\d{1,2}/\s+)', '', trf_out_date)  # Strip blank or invalid dates
    return trf_out_date


def get_date_of_death(row):
    date_of_death = row['Date of Death']
    date_of_death = re.sub(r'^(\s+/\s+/\s+)|(\d{1,2}/\d{1,2}/\s+)', '', date_of_death)  # Strip blank or invalid dates
    return date_of_death


#######################################################################################################################
# Straight column rename mapping
#######################################################################################################################

def convert_family_position(value, row):
    """Field is remapped as follows:
    'Head of Household' -> 'Primary contact',
    'Spouse' -> 'Spouse',
    'Son' -> 'Child',
    'Daughter' -> 'Child',
    <anything_else> -> 'Other'"""

    # TODO
    return ''


def convert_prefix(value, row):
    """Field is remapped as follows:
    'Rev.' -> 'Rev.',
    'Dr.' -> 'Dr.',
    'Mr.' -> 'Mr.',
    'Pastor' -> 'Pastor',
    'Ms.' -> 'Ms.',
    'Mrs.' -> 'Mrs.',
    <anything_else> -> ''"""

    # TODO
    return ''


def convert_suffix(value, row):
    """Field which is remapped as follows:
    'Jr.' -> 'Jr.',
    'Sr.' -> 'Sr.',
    'II' -> 'II',
    'III' -> 'III',
    'IV' -> 'IV',
    'Dr.' -> 'Dr.',
    <anything_else> -> ''"""

    # TODO
    return ''


def handle_field_mappings(table):

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

    sk_fields_renamed = set()

    field_mappings = [

        ('family id', 'Family ID'),
        ('individual id', 'Individual ID'),
        ('Relationship', 'family position', convert_family_position),
        ('prefix', 'Title', convert_prefix),
        ('first name', 'Preferred Name'),
        ('middle name', 'Middle Name'),
        ('last name', 'Last Name'),
        ('suffix', 'Suffix', convert_suffix),
        ('legal name', 'First Name'),
        ('Limited Access User', '', '<limited_access_setting>'),
        ('Listed', None, convert_listed),
        ('inactive/remove', 'Active Profile', convert_inactive_remove),
        ('campus', None, 'Ingomar Church'),
        ('email', 'Individual e-Mail'),
        ('mailing street', 'Address'),
        ('mailing street line 2', 'Address Line 2'),
        ('city', 'City'),
        ('state', 'State'),
        ('postal code', 'Zip Code'),
        ('country', 'Country'),
        ('mailing carrier route'),
        ('home street', 'Address'),
        ('home street line 2', 'Address Line 2'),
        ('home_city', 'City'),
        ('home_state', 'State'),
        ('home_postal code', 'Zip Code'),
        ('area_of_town'),
        ('contact_phone', None, convert_contact_phone),
        ('Home Phone', 'home phone', convert_phone),
        ('Work Phone', 'work phone', convert_phone),
        ('Cell Phone', 'cell phone', convert_phone),
        ('service provider'),
        ('fax'),
        ('pager'),
        ('emergency phone'),
        ('emergency contact name'),

        ('Birth Date', 'birthday', convert_date),
        ('Wedding Date', 'anniversary', convert_date),
        ('Gender', 'gender', convert_gender),
        ('Env #', 'giving #'),
        ('Marital Status', 'marital status', convert_marital_status),
        ('Date Joined', 'membership date', convert_date),
        ('Trf out/Withdrawal Date', 'membership stop date', convert_date),
        ('membership type', None, convert_membership_type),
        ('Baptized', 'baptized', convert_baptized),
        ('School District', 'school'),
        ('school grade'),
        ('known allergies'),
        ('confirmed no allergies'),
        ('notes', None, convert_notes),
        ('approved to work with children', None, convert_approved_to_work_with_children),
        ('approved to work with children stop date', None, convert_approved_to_work_with_children_stop_date),
        ('commitment date'),
        ('how they heard', None, convert_how_they_heard),
        ('how they joined', None, convert_how_they_joined),
        ('reason left church', None, convert_reason_left_church),
        ('Occupation', 'job title'),
        ('work street 1'),
        ('work street 2'),
        ('work city'),
        ('work state'),
        ('work postal code'),
        ('Current Story'),
        ('Commitment Story'),
        ('Date of Death', 'deceased', convert_date),
        ('facebook_username'),
        ('twitter_username'),
        ('blog_username'),
        ('website my'),
        ('website work'),
        ('military'),  # Anything from Carol?
        ('spiritual_maturity'),
        ('spiritual_gifts', None, convert_spiritual_gifts),
        ('passions', None, convert_spiritual_passions),
        ('abilities/skills', None, convert_abilities_skills),
        ('church_services_I_attend'),
        ('personal_style'),

        # No such thing as 'other' address info in silver_sample file, but they're valid fields
        ('Alt Address', 'other street'),
        ('Alt Address Line 2', 'other street line 2'),
        ('Alt City', 'other city'),
        ('Alt Country', 'other country'),
        ('Alt State', 'other state'),
        ('Alt Zip Code', 'other_postal code'),

        # Guest folloowup process queue
        ('1-Month Follow-up', 'guest_followup 1 month', None, 'process_queue'),
        ('Wk 1 Follow-up', 'guest_followup 1 week', None, 'process_queue'),
        ('Wk 2 Follow-up', 'guest_followup 2 weeks', None, 'process_queue'),

        # Burial folloowup process queue
        ('Burial: City, County, St', 'burial city county state', None, 'process_queue'),
        ('Burial: Date', 'burial date', convert_date, 'process_queue'),
        ('Burial: Officating Pastor', 'burial officiating pastor', None, 'process_queue'),
        ('Burial: Site Title', 'burial site title', None, 'process_queue'),

        # Custom fields
        ('Baptized Date', 'baptism date', convert_date, 'custom-pulldown'),
        ('Baptized by', 'baptized by', None, 'custom-pulldown'),
        ('Confirmed Date', 'confirmed date', convert_date, 'custom-date'),
        ('Confirmed', 'confirmed', convert_confirmed, 'custom-pulldown'),
        ('Mail Box #', 'mailbox number', None, 'custom-text'),
        ('The Spirit Mailing', 'spirit mailing', convert_spirit_mailing, 'custom-pulldown'),
        ('Photo Release', 'photo release', convert_photo_release, 'custom-pulldown'),
        ('Racial/Ethnic identification', 'ethnicity', convert_ethnicity, 'custom-pulldown'),
        ('Church Transferred From', 'church transferred from', None, 'custom-text'),
        ('Church Transferred To', 'church transferred to', None, 'custom-text'),
        ('Pastor when joined', 'pastor when joined', None, 'custom-text'),
        ('Pastor when leaving', 'pastor when leaving', None, 'custom-text')
    ]

    # TODO - Rewrite logic to walk structure above (keep track of SK fields used so on 2nd hit, don't rename field,
    # clone field instead).  Also make sure to somehow stash columns used by xref mappers

    cut_keys = [tuple[0] for tuple in column_renames]
    rename_dict = {tuple[0]: tuple[1] for tuple in column_renames}

    table_ccb_columns = petl.cut(table, cut_keys)

    return petl.rename(table_ccb_columns, rename_dict)


if __name__ == "__main__":
    main(sys.argv[1:])
