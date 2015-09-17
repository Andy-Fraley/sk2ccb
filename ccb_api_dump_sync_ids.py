#!/usr/bin/env python


import sys
import pycurl
import tempfile
import xml.etree.ElementTree as ET
import os
from StringIO import StringIO
from settings import settings


def main(argv):
    tmp_filename = http_get2tmp_file('https://ingomar.ccbchurch.com/api.php?srv=individual_profiles',
        settings.ccbapi.username, settings.ccbapi.password)
    tree = ET.parse(tmp_filename)
    root = tree.getroot()
    for individual in root.findall('./response/individuals/individual'):
        sync_id = individual.get('sync_id')
        if not sync_id:
            sync_id = '<None>'
        print individual.attrib['id'], sync_id
    # os.remove(tmp_filename)
    print tmp_filename
    sys.exit(1)



    parser = argparse.ArgumentParser()
    parser.add_argument("--output-filename", required=True, help="Output CSV filename which will be loaded with "
        "<individual_id>, <sync_id> pairings dumped for every individual in CCB")
    args = parser.parse_args()

    print settings.ccbapi.username + ':' + settings.ccbapi.password

    buffer = StringIO()
    c = pycurl.Curl()
    c.setopt(c.URL, 'https://ingomar.ccbchurch.com/api.php?srv=individual_profiles')
    c.setopt(c.WRITEDATA, buffer)
    c.setopt(c.USERPWD, 'afraley@ingomarchurch.org:2jXxgB2N2JHpa97J67g8')
    # c.setopt(pycurl.USERPWD, settings.ccbapi.username + ':' + settings.ccbapi.password)
    c.perform()
    c.close()
    body = buffer.getvalue()
    print(body)


    """
import pycurl
from StringIO import StringIO
buffer = StringIO()
c = pycurl.Curl()
c.setopt(c.URL, 'https://ingomar.ccbchurch.com/api.php?srv=individual_profiles')
c.setopt(c.USERPWD, 'afraley@ingomarchurch.org:2jXxgB2N2JHpa97J67g8')
c.setopt(c.WRITEDATA, buffer)
c.perform()
c.close()
body = buffer.getvalue()
print body
    """


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
