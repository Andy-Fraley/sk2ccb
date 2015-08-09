#!/usr/bin/env python


import sys, getopt, os.path, csv, argparse, petl


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

    individuals_input_table = petl.fromcsv(args.individuals_filename)
    individuals_output_table = transform_rename_columns(individuals_input_table)

    petl.tocsv(individuals_output_table, args.output_filename)


def transform_rename_columns(individuals_input_table):
    column_renames = {
        'Address': 'home street',
        'Address': 'mailing street',
        'Address Line 2': 'home street line 2',
        'Address Line 2': 'mailing street line 2',
        'Alt Address': 'other street',  # No such thing as 'other street' in silver_sample file
        'Alt Address Line 2': 'other street line 2',
        'Alt City': 'other city',
        'Alt Country': 'other country',
        'Alt State': 'other state',
        'Alt Zip Code': 'other_postal code',
        'Birth Date': 'birthday',
        'Cell Phone': 'cell phone',
        'City': 'home_city',
        'City': 'city',
        'Country': 'country',
        'Date of Death': 'deceased',
#        'Emergency Contact': 'emergency contact name',
#        'Emergency Phone': 'emergency phone',
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
        'State': 'home state',
        'Suffix': 'suffix',
        'Title': 'prefix',
        'Racial/Ethnic identification': 'ethnicity',
        'Relationship': 'family position',
        'Wedding Date': 'anniversary',
        'Work Phone': 'work phone',
        'Zip Code': 'home_postal code',
        'Zip Code': 'postal code',
        'Env #': 'giving #',
        'The Spirit Mailing': 'spirit mailing',
        'Baptized': 'baptized',
        'Baptized by': 'baptized by',
        'Baptized Date': 'baptized date',
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

    individuals_output_table = petl.rename(individuals_input_table, column_renames)
    return individuals_output_table


if __name__ == "__main__":
    main(sys.argv[1:])
