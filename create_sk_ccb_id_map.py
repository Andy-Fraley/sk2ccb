#!/usr/bin/env python


import sys
import os.path
import argparse
import csv


def main(argv):

    parser = argparse.ArgumentParser()
    parser.add_argument("--sk-individuals-filename", required=True, help="Input UTF8 CSV with individuals data " \
        "dumped from Servant Keeper")
    parser.add_argument("--ccb-id-info-filename", required=True, help="Input CSV with ID info like first_name, " \
        "last_name, etc., from CCB.")
    parser.add_argument("--output-individual-map-filename", required=True, help="Output CSV filename which will be " \
        "loaded with sk_individual_id, ccb_individual_id mappings")
    parser.add_argument("--output-family-map-filename", required=True, help="Output CSV filename which will be " \
        "loaded with sk_family_id, ccb_family_id mappings")
    args = parser.parse_args()

    assert os.path.isfile(args.sk_individuals_filename), "Error: cannot open file '" + \
        args.sk_individuals_filename + "'"
    # assert os.path.isfile(args.ccb_id_info_filename), "Error: cannot open file '" + \
    #     args.ccb_id_info_filename + "'"

    dict_sk_individuals = {}  # Keyed by last name, maps to list of dicts for that last name, each with id fields
    with open(args.sk_individuals_filename) as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            dict_to_add = dict_from_row(row, {'Individual ID': 'sk_individual_id', 'Family ID':'sk_family_id',
                'Preferred Name': 'first name', 'First Name': 'legal name', 'Middle Name': 'middle name',
                'Last Name': 'last name', 'Title':'prefix', 'Suffix':'suffix'})
            if row['Last Name'] not in dict_sk_individuals:
                dict_sk_individuals[row['Last Name']] = []
            dict_sk_individuals[row['Last Name']].append(dict_to_add)

    sk_ccb_individual_matches = {}
    sk_ccb_family_matches = {}
    with open(args.ccb_id_info_filename) as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            tuple_ids = match_on_fields(row, dict_sk_individuals, ['first name', 'legal name', 'middle name',
                'last name', 'prefix', 'suffix']):
            if tuple_ids:
                match_type = 'matched all fields'
            else:
                tuple_ids = match_on_fields(row, dict_sk_individuals, ['first name', 'last name'])
                if tuple_ids:
                    match_type = 'matched only on first and last name'
                else:
                    print << sys.stderr, '*** WARNING! Cannot find match in CCB for SK record: ' + str(row)
            if tuple_ids:
                sk_ccb_individual_matches[tuple_ids[0]] = [tuple_ids[1], match_type]
                sk_ccb_family_matches[tuple_ids[2]] = [tuple_ids[3], match_type]

    print sk_ccb_individual_matches
    print sk_ccb_family_matches

    sys.exit(1)


def match_on_fields(row, dict_sk_individuals, fields_list):
    last_name = row['last name']
    if last_name not in dict_sk_individuals:
        return None
    for dict_sk_fields in dict_sk_individuals[last_name]:
        matched = True
        for field in fields_list:
            if dict_sk_fields[field] != row[field]:
                matched = False
                break
        if matched:
            return (dict_sk_fields['Individual ID'], row['!!!


def dict_from_row(row, dict_fields):
    dict_return = {}
    for key in dict_fields:
        dict_return[dict_fields[key]] = row[key]
    return dict_return


if __name__ == "__main__":
    main(sys.argv[1:])
