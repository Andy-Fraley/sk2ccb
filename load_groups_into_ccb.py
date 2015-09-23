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
    sk_indiv_id2name = gather_name_by_indiv_id(table)

    trace('RETRIEVING GROUPS XML FROM CCB...', args.trace, banner=True)
    tmp_filename = http_get2tmp_file('https://ingomar.ccbchurch.com/api.php?srv=group_profiles',
        settings.ccbapi.username, settings.ccbapi.password)
    xml_tree = ET.parse(tmp_filename)
    xml_root = xml_tree.getroot()

    group_id_map_dict = xml2group_id_dict(xml_root)
    os.remove(tmp_filename)

    # print group_id_map_dict

    # Given mapping dict of SK ID to CCB ID (sk2ccb_id_map_dict)
    # Given mapping of SK ID to list of SK group names that ID is member of (sk_indiv_id2groups)
    # Given mapping of SK group name to CCB group ID (group_id_map_dict)
    #
    # Now do the work and add individuals to groups in CCB

    for sk_indiv_id in sk_indiv_id2groups:
        if sk_indiv_id in sk2ccb_id_map_dict:
            for group_name in sk_indiv_id2groups[sk_indiv_id]:
                if not group_name in group_id_map_dict:
                    print "*** Cannot find CCB group name '" + group_name + "' in CCB account."
                print "Adding " + sk_indiv_id2name[sk_indiv_id] + " to group '" + group_name + "'."
        else:
            groups_trying_to_add = ', '.join(sk_indiv_id2groups[sk_indiv_id])
            print "*** Cannot find CCB individual ID for sk_indiv_id '" + \
                str(sk_indiv_id) + "' (" + sk_indiv_id2name[sk_indiv_id] + ") in CCB account (via custom " + \
                "property 'SK Indiv ID'). Therefore, cannot add this person to " + groups_trying_to_add + "."


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


def gather_name_by_indiv_id(table):
    sk_indiv_id2name = {}
    for row in petl.records(table):
        sk_indiv_id2name[row['Individual ID']] = row['Preferred Name'] + ' ' + row['Last Name']
    return sk_indiv_id2name


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


def xml2group_id_dict(xml_root):
    group_id_map_dict = {}
    ccb_group_name_map = {'Rummage Sale Mailing': 'Rummage Sale', 'Home Touch Mailing': 'Home Touch',
        'Veterans': 'Veteran', 'Wesleyan Choir': 'Wesleyan Choir', 'Celebration Singers': 'Celebration Singers',
        'Praise Team': 'Praise Team'}
    for group in xml_root.findall('./response/groups/group'):
        group_id = group.attrib['id']
        group_name = group.find('name').text
        if group_name in ccb_group_name_map:
            # assert group.find('interaction_type').text == 'Administrative', "Found group named '" + group_name + \
            #     "' in CCB, however it is NOT type 'Administrative', so aborting...."
            from_name = ccb_group_name_map[group_name]
            group_id_map_dict[from_name] = group_id
    return group_id_map_dict


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
