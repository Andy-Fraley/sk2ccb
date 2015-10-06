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
