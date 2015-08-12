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

    input_table = petl.fromcsv(args.individuals_filename)
    transform_pipeline = get_transform_pipeline()
    output_table = execute_transform_pipeline(transform_pipeline, input_table)
    petl.tocsv(output_table, args.output_filename)


def match_replace(input_values, match_replace_list):
    output_values = []
    for value in input_values:
        for match_replace in match_replace_list:
            value = re.sub(match_replace[0], match_replace[1], value)
        output_values.append(value)
    return output_values


def strip_empty_and_incomplete_dates(input_values):
    return match_replace(input_values, [(r'^\s+/\s+/\s+$', ''), (r'^\d{1,2}/\d{1,2}/\s+$','')])


def strip_empty_phone_numbers(input_values):
    return match_replace(input_values, [(r'^\s+\-\s+\-\s+$', '')])


def execute_transform_pipeline(transform_pipeline, input_table):
    output_table = petl.empty()
    for transform_node in transform_pipeline:
        input_column_names = transform_node['input']
        input_columns = petl.values(input_table, input_column_names)
        pre_validator = transform_node['pre_validator']
        if pre_validator:
            pre_validator(input_columns)
        transforms = transform_node['transforms']
        if transforms:
            prior_output_column = None
            for transform in transforms:
                if prior_output_column:
                    output_column = transform(prior_output_column)
                else:
                    output_column = transform(input_columns)
                prior_output_column = output_column
        else:
            if len(input_column_names) == 1:
                output_column = input_columns
            else:
                print >> sys.stderr, "*** Error!  No (reducing) transform(s) specified but more than one input " \
                    "column"
                print >> sys.stderr, transform_node
                sys.exit(1)
        post_validator = transform_node['post_validator']
        if post_validator:
            post_validator(output_column)
        output_table = petl.addcolumn(output_table, transform_node['output'], output_column)
    return output_table


def get_transform_pipeline():
    transform_pipeline = [
        {
            'input': ['Address'],
            'pre_validator': None,
            'transforms': None,
            'output': 'home street',
            'post_validator': None
        },

        {
            'input': ['Birth Date'],
            'pre_validator': None,
            'transforms': [strip_empty_and_incomplete_dates],
            'output': 'birthday',
            'post_validator': None
        },

        {
            'input': ['Cell Phone'],
            'pre_validator': None,
            'transforms': [strip_empty_phone_numbers],
            'output': 'cell phone',
            'post_validator': None
        }

    ]

    return transform_pipeline


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
