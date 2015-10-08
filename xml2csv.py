#!/usr/bin/env python

import petl
import sys
import argparse

def main(argv):

    urls = {
        'INDIVIDUALS': {
            'xmlroot': 'response/individuals/individual',
            'parse_dict': {
                'Family ID': ('family', 'id'),
                'Individual ID': ('.', 'id'),
                'Family Position': 'family_position',
                'Prefix': 'salutation',
                'First Name': 'first_name',
                'Middle Name': 'middle_name',
                'Last Name': 'last_name',
                'Legal Name': 'legal_first_name',
                'Legal Name': 'legal_first_name',
                'Active': 'active',
                'Campus': 'campus',
                'Email': 'email',

                'Mailing Street': ".//address[@type='mailing']/street_address",
                'Mailing City': ".//address[@type='mailing']/city",
                'Mailing State': ".//address[@type='mailing']/state",
                'Mailing Postal Code': ".//address[@type='mailing']/zip",
                'Mailing Country': ".//address[@type='mailing']/country",

                'Home Street': ".//address[@type='home']/street_address",
                'Home City': ".//address[@type='home']/city",
                'Home State': ".//address[@type='home']/state",
                'Home Postal Code': ".//address[@type='home']/zip",
                'Home Country': ".//address[@type='home']/country",

                'Other Street': ".//address[@type='other']/street_address",
                'Other City': ".//address[@type='other']/city",
                'Other State': ".//address[@type='other']/state",
                'Other Postal Code': ".//address[@type='other']/zip",
                'Other Country': ".//address[@type='other']/country",

                'Contact Phone': ".//phone[@type='contact']",
                'Home Phone': ".//phone[@type='home']",
                'Work Phone': ".//phone[@type='work']",
                'Mobile Phone': ".//phone[@type='mobile']",
                'Emergency Phone': ".//phone[@type='emergency']",

                'Birthday': 'birthday',
                'Anniversary': 'anniversary',
                'Gender': 'gender',
                'Giving Number': 'giving_number',
                'Marital Status': 'marital_status',
                'Membership Start Date': 'membership_date',
                'Membership End Date': 'membership_end',
                'Membership Type': 'membership_type',
                'Baptized': 'baptized',
                # 'School District': ??,
                # 'How They Heard': ??,
                # 'How They Joined': ??,
                # 'Reason Left Church': ??,
                # 'Job Title': ??,
                'Deceased': 'deceased',

                # !!!

                'Baptism Date': ".//user_defined_date_fields/user_defined_date_field[label='Baptism Date']/date",
                'Baptized By': ".//user_defined_text_fields/user_defined_text_field[label='Baptized By']/text",
                'Confirmed Date': ".//user_defined_date_fields/user_defined_date_field[label='Confirmed Date']/date",
                'Confirmed': ".//user_defined_pulldown_fields/user_defined_pulldown_field[label='Confirmed']/selection",
                'Mailbox Number': ".//user_defined_text_fields/user_defined_text_field[label='Mailbox Number']/text",
                'Spirit Mailing': ".//user_defined_pulldown_fields/user_defined_pulldown_field[label='Spirit Mailing']/selection",
                'Photo Release': ".//user_defined_pulldown_fields/user_defined_pulldown_field[label='Photo Release']/selection",
                'Ethnicity': ".//user_defined_pulldown_fields/user_defined_pulldown_field[label='Ethnicity']/selection",
                'Transferred Frm': ".//user_defined_text_fields/user_defined_text_field[label='Transferred Frm']/text",
                'Transferred To': ".//user_defined_text_fields/user_defined_text_field[label='Transferred To']/text",
                'Pastr When Join': ".//user_defined_text_fields/user_defined_text_field[label='Pastr When Join']/text",
                'Pastr When Leav': ".//user_defined_text_fields/user_defined_text_field[label='Pastr When Leav']/text",
                'SK Indiv ID': ".//user_defined_text_fields/user_defined_text_field[label='SK Indiv ID']/text"
            }
        },
        'GROUPS': 'https://ingomar.ccbchurch.com/api.php?srv=group_profiles',
        'ACCOUNTS': 'https://ingomar.ccbchurch.com/api.php?srv=transaction_detail_type_list',
        'TRANSACTIONS': {
            'xmlroot': 'response/batches/batch/transactions/transaction',
            'parse_dict': {
                'Date': 'date',
                'Payment Type': 'payment_type',
                'Check Number': 'check_number',
                'Individual ID': ('individual', 'id'),
                'Account': './/transaction_details/transaction_detail/coa',
                'Amount': './/transaction_details/transaction_detail/amount',
                'Tax Deductible': './/transaction_details/transaction_detail/tax_deductible',
                'Note': './/transaction_details/transaction_detail/note'
            }
        }
    }

    parser = argparse.ArgumentParser(description="Parses XML file into CSV output")
    parser.add_argument("--type", required=True, help='One of ' + ', '.join(urls.keys()))
    parser.add_argument("--xml-input-filename", required=True, help="XML file to parse")
    parser.add_argument("--csv-output-filename", required=True, help="CSV output file")
    args = parser.parse_args()

    table1 = petl.fromxml(args.xml_input_filename, urls[args.type]['xmlroot'], urls[args.type]['parse_dict'])
    petl.tocsv(table1, args.csv_output_filename)


if __name__ == "__main__":
    main(sys.argv[1:])
