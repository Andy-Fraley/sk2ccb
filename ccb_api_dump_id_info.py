#!/usr/bin/env python


import sys
import pycurl
import tempfile
import xml.etree.ElementTree as ET
import os
import argparse
from StringIO import StringIO
from settings import settings


def main(argv):
    parser = argparse.ArgumentParser(description='Dumps CSV-formatted ID-related info for every individual profile ' \
        'in CCB.  Pipe into a file to create CSV file.')
    args = parser.parse_args()

    tmp_filename = http_get2tmp_file('https://ingomar.ccbchurch.com/api.php?srv=individual_profiles',
        settings.ccbapi.username, settings.ccbapi.password)
    tree = ET.parse(tmp_filename)
    root = tree.getroot()
    print 'individual_id,family_id,prefix,legal_name,first_name,middle_name,last_name,suffix'
    for individual in root.findall('./response/individuals/individual'):
        family_id = get_family_id(individual)
        prefix = node_text(individual, 'prefix')
        legal_name = node_text(individual, 'legal_name')
        first_name = node_text(individual, 'first_name')
        middle_name = node_text(individual, 'middle_name')
        last_name = node_text(individual, 'last_name')
        suffix = node_text(individual, 'suffix')
        print individual.attrib['id'] + ',' + family_id + ',' + prefix + ',' + legal_name + ',' + first_name + ',' + \
            middle_name + ',' + last_name + ',' + suffix
    os.remove(tmp_filename)


def node_text(node, tag):
    if node.find(tag) is not None and node.find(tag).text is not None:
        return node.find(tag).text
    else:
        return ''


def get_family_id(node):
    family_node = node.find('family')
    family_id = ''
    if family_node is not None:
        if 'id' in family_node.attrib:
            family_id = family_node.attrib['id']
    return family_id


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


if __name__ == "__main__":
    main(sys.argv[1:])
