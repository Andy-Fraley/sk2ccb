#!/usr/bin/env python

import petl
import sys
import argparse

def main(argv):

    urls = {
        'INDIVIDUALS': {
            'xmlroot': 'response/individuals/individual',
            'parse_dict': {
                'individual_id': ('.', 'id'),
                'first_name':'first_name',
                'last_name':'last_name',
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
        'TRANSACTIONS': 'https://ingomar.ccbchurch.com/api.php?srv=batch_profiles'
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
