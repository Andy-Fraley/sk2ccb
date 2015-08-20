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

    table = petl.fromcsv(args.individuals_filename)

    # Drop out all rows in Servant Keeper marked as 'Active Profile' != 'Yes' (i.e. == 'No')
    # table = petl.select(table, "{Active Profile} == 'Yes'")

    """
    table = rename_columns(table)

    # Remove empty dates and dates missing year
    regex_empty_dates = r'^(\s+/\s+/\s+)|(\d{1,2}/\d{1,2}/\s+)'
    table = petl.sub(table, 'birthday', regex_empty_dates, '')
    table = petl.sub(table, 'deceased', regex_empty_dates, '')
    table = petl.sub(table, 'anniversary', regex_empty_dates, '')
    table = petl.sub(table, 'baptized date', regex_empty_dates, '')
    table = petl.sub(table, 'pq__burial date', regex_empty_dates, '')
    table = petl.sub(table, 'confirmed date', regex_empty_dates, '')
    table = petl.sub(table, 'membership date', regex_empty_dates, '')
    table = petl.sub(table, 'membership stop date', regex_empty_dates, '')
    table = petl.sub(table, 'pq__guest_followup 1 month', regex_empty_dates, '')
    table = petl.sub(table, 'pq__guest_followup 1 week', regex_empty_dates, '')
    table = petl.sub(table, 'pq__guest_followup 2 weeks', regex_empty_dates, '')

    # Remove empty phone numbers
    regex_empty_phones = r'^\s+\-\s+\-\s+$'
    table = petl.sub(table, 'cell phone', regex_empty_phones, '')
    table = petl.sub(table, 'home phone', regex_empty_phones, '')
    table = petl.sub(table, 'work phone', regex_empty_phones, '')

    # Clones
    table = petl.addfield(table, 'sync id', lambda rec: rec['individual id'])
    table = petl.addfield(table, 'mailing street', lambda rec: rec['home street'])
    table = petl.addfield(table, 'mailing street line 2', lambda rec: rec['home street line 2'])
    table = petl.addfield(table, 'home_city', lambda rec: rec['city'])
    table = petl.addfield(table, 'home_state', lambda rec: rec['state'])
    table = petl.addfield(table, 'home_postal code', lambda rec: rec['postal code'])

    # Simple remaps
    table = petl.convert(table, 'inactive/remove', {'Yes': '', 'No': 'yes'})
    """

    # Do the xref mappings specified in 'XRef-Member Status' tab of mapping spreadsheet
    xref_member_fields = get_xref_member_fields()
    table = petl.addfield(table, 'ccb__membership type', get_membership_type)
    table = petl.addfield(table, 'ccb__inactive/remove', get_inactive_remove)
    table = petl.addfield(table, 'ccb__membership date', get_membership_date)
    table = petl.addfield(table, 'ccb__reason left', get_reason_left)
    table = petl.addfield(table, 'ccb__membership stop date', get_membership_stop_date)
    table = petl.addfield(table, 'ccb__deceased', get_deceased)

    # Do single xref mapping specified in 'XRef-How Sourced' tab of mapping spreadsheet
    xref_how_sourced = get_xref_how_sourced()
    table = petl.addfield(table, 'ccb_how they heard', get_how_they_heard)

    # Do xref mappings specified in 'XRef-W2S, Skills, SGifts' tab of mapping spreadsheet
    xref_w2s_skills_sgifts = get_xref_w2s_skills_sgifts()
    semicolon_sep_fields = {}
    init_hitmiss_counters(xref_w2s_skills_sgifts)
    gather_semicolon_sep_field(semicolon_sep_fields, table, 'Willing to Serve')
    gather_semicolon_sep_field(semicolon_sep_fields, table, 'Skills')
    gather_semicolon_sep_field(semicolon_sep_fields, table, 'Spiritual Gifts')
    table = petl.addfield(table, 'ccb__passions', get_gathered_passions)
    table = petl.addfield(table, 'ccb__abilities', get_gathered_abilities)
    table = petl.addfield(table, 'ccb__spiritual_gifts', get_gathered_spiritual_gifts)

    # print semicolon_sep_fields

    # print hitmiss_counters
    # for sk_field in hitmiss_counters:
    #    for item in hitmiss_counters[sk_field]:
    #        print >> sys.stderr, sk_field + ';' + item + ';' + str(hitmiss_counters[sk_field][item])

    petl.tocsv(table, args.output_filename)


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

def rename_columns(table):
    column_renames = {
        'Family ID': 'family id',
        'Individual ID': 'individual id',
        'Active Profile': 'inactive/remove',
        'Address': 'home street',
        'Address Line 2': 'home street line 2',
        'Alt Address': 'other street',  # No such thing as 'other street' in silver_sample file
        'Alt Address Line 2': 'other street line 2',
        'Alt City': 'other city',
        'Alt Country': 'other country',
        'Alt State': 'other state',
        'Alt Zip Code': 'other_postal code',
        'Birth Date': 'birthday',
        'Cell Phone': 'cell phone',
        'City': 'city',
        'Country': 'country',
        'Date of Death': 'deceased',
        'First Name': 'legal name',
        'Gender': 'gender',
        'Home Phone': 'home phone',
        'Individual e-Mail': 'email',
        'Last Name': 'last name',
        'Mail Box #': 'mailbox number',
        'Marital Status': 'marital status',
        'Middle Name': 'middle name',
        'Occupation': 'job title',
        'Photo Release': 'photo release',
        'Preferred Name': 'first name',
        'School District': 'school',
        'State': 'state',
        'Suffix': 'suffix',
        'Title': 'prefix',
        'Racial/Ethnic identification': 'ethnicity',
        'Relationship': 'family position',
        'Wedding Date': 'anniversary',
        'Work Phone': 'work phone',
        'Zip Code': 'postal code',
        '1-Month Follow-up': 'pq__guest_followup 1 month',
        'Wk 1 Follow-up': 'pq__guest_followup 1 week',
        'Wk 2 Follow-up': 'pq__guest_followup 2 weeks',
        'Env #': 'giving #',
        'The Spirit Mailing': 'spirit mailing',
        'Baptized': 'baptized',
        'Baptized by': 'baptized by',
        'Baptized Date': 'baptized date',
        'Burial: City, County, St': 'pq__burial city county state',
        'Burial: Date': 'pq__burial date',
        'Burial: Officating Pastor': 'pq__burial officiating pastor',
        'Burial: Site Title': 'pq__burial site title',
        'Church Transferred From': 'church transferred from',
        'Church Transferred To': 'church transferred to',
        'Confirmed': 'confirmed',
        'Confirmed Date': 'confirmed date',
        'Date Joined': 'membership date',
        # 'How Joined': 'how they joined',
        # 'Member Status': 'membership type',
        'Pastor when joined': 'pastor when joined',
        'Pastor when leaving': 'pastor when leaving',
        'Trf out/Withdrawal Date': 'membership stop date'
    }

    return petl.rename(table, column_renames)


if __name__ == "__main__":
    main(sys.argv[1:])
