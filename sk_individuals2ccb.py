#!/usr/bin/env python


import sys, getopt, os.path, csv, argparse, petl, re


def main(argv):
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

    petl.tocsv(table, args.output_filename)


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
        'How Joined': 'how they joined',
        'Member Status': 'membership type',
        'Pastor when joined': 'pastor when joined',
        'Pastor when leaving': 'pastor when leaving',
        'Trf out/Withdrawal Date': 'membership stop date'
    }

    return petl.rename(table, column_renames)


if __name__ == "__main__":
    main(sys.argv[1:])
