#!/usr/bin/env python


import sys
import pycurl
import tempfile
import xml.etree.ElementTree as ET
import os
import argparse
from StringIO import StringIO
from settings import settings
import petl


def main(argv):
    parser = argparse.ArgumentParser(description='Dumps CSV-formatted ID-related info for every individual profile ' \
        'in CCB.  Pipe into a file to create CSV file.')
    parser.add_argument("--individuals-filename", required=True, help="Input UTF8 CSV with individuals data "
        "dumped from Servant Keeper")
    parser.add_argument('--trace', action='store_true', help="If specified, prints tracing/progress messages to "
        "stdout")
    args = parser.parse_args()

    assert os.path.isfile(args.individuals_filename), "Error: cannot open file '" + args.individuals_filename + "'"

    trace('RETRIEVING INDIVIDUALS XML FROM CCB...', args.trace, banner=True)
    tmp_filename = http_get2tmp_file('https://ingomar.ccbchurch.com/api.php?srv=individual_profiles',
        settings.ccbapi.username, settings.ccbapi.password)
    xml_tree = ET.parse(tmp_filename)
    xml_root = xml_tree.getroot()

    trace('WALKING XML TO CREATE SK2CCB ID MAP DICTIONARY...', args.trace, banner=True)
    sk2ccb_id_map_dict = xml2id_dict(xml_root)
    os.remove(tmp_filename)

    trace('WALKING SK DATA TO IDENTIFY GROUPS TO SET ON PER-INDIVIDUAL BASIS...', args.trace, banner=True)
    table = petl.fromcsv(args.individuals_filename)
    sk_indiv_id2groups = gather_semi_sep_by_indiv_id(table, {'Mailing Lists': ['Home Touch', 'Rummage Sale'],
        'Activities': ['Veteran', 'Celebration Singers', 'Wesleyan Choir', 'Praise Team']})

    print sk_indiv_id2groups

    # TODO - Query CCB's Admin Group IDs for Group list:
    #   ['Home Touch', 'Rummage Sale', 'Veteran', 'Celebration Singers', 'Wesleyan Choir', 'Praise Team']
    # Confirm Admin Group ID for each exists...
    # Then given those Group IDs, call CCB API to associate IDs with those Groups in CCB


def gather_semi_sep_by_indiv_id(table, dict_semi_column_fields):
    dict_id2groups = {}
    for row in petl.records(table):
        for col in dict_semi_column_fields:
            field_list = dict_semi_column_fields[col]
            value = row[col].strip()
            if value == '':
                continue
            else:
                sk_indiv_id = row['Individual ID']
                for group_name in value.split(';'):
                    group_name_str = group_name.strip()
                    if group_name_str in field_list:
                        if not sk_indiv_id in dict_id2groups:
                            dict_id2groups[sk_indiv_id] = []
                        dict_id2groups[sk_indiv_id].append(group_name_str)
    return dict_id2groups


def xml2id_dict(xml_root):
    sk2ccb_id_map_dict = {}
    for individual in xml_root.findall('./response/individuals/individual'):
        ccb_indiv_id = individual.attrib['id']
        sk_indiv_id = None
        for udf_text in individual.findall('./user_defined_text_fields/user_defined_text_field'):
            if udf_text.find('label').text == 'SK Indiv ID':
                sk_indiv_id = udf_text.find('text').text
        if sk_indiv_id:
            sk2ccb_id_map_dict[sk_indiv_id] = ccb_indiv_id
    return sk2ccb_id_map_dict


def node_text(node, tag):
    if node.find(tag) is not None and node.find(tag).text is not None:
        return node.find(tag).text
    else:
        return ''


def http_get2tmp_file(url, username, password):
    with tempfile.NamedTemporaryFile(delete=False) as temp:
        tmp_filename = temp.name
        temp.close()
    with open(tmp_filename, 'wb') as file_w:
        c = pycurl.Curl()
        c.setopt(c.URL, url)
        c.setopt(c.USERPWD, username + ':' + password)
        c.setopt(c.WRITEDATA, file_w)
        c.perform()
        c.close()
        file_w.close()
    return tmp_filename


def trace(msg_str, trace_flag, banner=False):
    if trace_flag:
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


if __name__ == "__main__":
    main(sys.argv[1:])
