#!/usr/bin/env python


import sys
import pycurl
import tempfile
import xml.etree.ElementTree as ET
import os
import argparse
import petl
from StringIO import StringIO
from settings import settings
import urllib


def main(argv):
    parser = argparse.ArgumentParser(description='Dumps CSV-formatted ID-related info for every individual profile ' \
        'in CCB.  Pipe into a file to create CSV file.')
    parser.add_argument("--individuals-filename", required=True, help="Input UTF8 CSV with individuals data "
        "dumped from Servant Keeper")
    parser.add_argument("--output-csv-filename", required=True, help="Output CSV with two columns, SK ID and " \
        "CCB ID")
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

    trace('WRITE SK AND CCB IDS TO CSV FILE...', args.trace, banner=True)
    with open(args.output_csv_filename, 'wb') as output_file:
        output_file.write('SK ID,CCB ID\n')
        for sk_id in sk2ccb_id_map_dict:
            output_file.write(sk_id + ',' + sk2ccb_id_map_dict[sk_id] + '\n')

    sys.stdout.flush()
    sys.stderr.flush()


def xml2id_dict(xml_root):
    sk2ccb_id_map_dict = {}
    ccb2sk_id_map_dict = {}
    for individual in xml_root.findall('./response/individuals/individual'):
        ccb_indiv_id = individual.attrib['id']
        sk_indiv_id = None
        for udf_text in individual.findall('./user_defined_text_fields/user_defined_text_field'):
            if udf_text.find('label').text == 'SK Indiv ID':
                sk_indiv_id = udf_text.find('text').text
        if sk_indiv_id:
            assert sk_indiv_id not in sk2ccb_id_map_dict, "SK Indiv ID '" + sk_indiv_id + "' was duplicated for " \
                "CCB IDs '" + sk2ccb_id_map_dict[sk_indiv_id] + "' and '" + ccb_indiv_id + "'"
            sk2ccb_id_map_dict[sk_indiv_id] = ccb_indiv_id
        if ccb_indiv_id:
            assert ccb_indiv_id not in ccb2sk_id_map_dict, "CCB Indiv ID '" + ccb_indiv_id + "' was duplicated for " \
                "SK Indiv IDs '" + ccb2sk_id_map_dict[ccb_indiv_id] + "' and '" + sk_indiv_id + "'"
            ccb2sk_id_map_dict[ccb_indiv_id] = sk_indiv_id
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


def http_post(url, data_dict, username, password):
    data_str = urllib.urlencode(data_dict)
    string_store = StringIO()
    c = pycurl.Curl()
    c.setopt(c.URL, url + '&' + data_str)
    c.setopt(c.USERPWD, username + ':' + password)
    c.setopt(pycurl.POST, 1)
    c.setopt(pycurl.POSTFIELDS, data_str)
    c.setopt(pycurl.WRITEDATA, string_store)
    # c.setopt(pycurl.VERBOSE, True)
    c.perform()
    return_code = c.getinfo(pycurl.HTTP_CODE)
    c.close()
    return return_code


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
