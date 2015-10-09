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
import datetime


class g:
    trace_flag = None


def main(argv):
    global g

    urls = {
        'INDIVIDUALS': 'https://ingomar.ccbchurch.com/api.php?srv=individual_profiles',
        'GROUPS': 'https://ingomar.ccbchurch.com/api.php?srv=group_profiles',
        'ACCOUNTS': 'https://ingomar.ccbchurch.com/api.php?srv=transaction_detail_type_list',
        'TRANSACTIONS': 'https://ingomar.ccbchurch.com/api.php?srv=batch_profiles'
    }

    parser = argparse.ArgumentParser(description="Creates time-stamped file per object type with contents of CCB " \
        "for that object type")
    parser.add_argument("--dump", required=True, nargs='*', default=argparse.SUPPRESS, help="One or more of " \
        + ', '.join(urls.keys()))
    parser.add_argument("--output-directory", required=False, help="Output directory for dumped XML files. " \
        "If not provided, then XML output files dumped to current directory.")
    parser.add_argument('--trace', action='store_true', help="If specified, prints trace output to stdout.")
    args = parser.parse_args()

    g.trace_flag = args.trace

    if args.output_directory:
        if not os.path.isdir(args.output_directory):
            print >> sys.stderr, "Path '" + args.output_directory + "' is not a valid directory."
            sys.exit(1)
        else:
            full_path = os.path.abspath(args.output_directory)
    else:
        full_path = '.'

    timestamp_str = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')

    trace("RETRIEVING XML VIA REST API AND STORING TO FILE(S)...", banner=True)

    for object_type in args.dump:
        assert object_type in urls, "No such object type '" + object_type + "' to dump from CCB."
        url = urls[object_type]
        filename = full_path + '/' + object_type.lower() + '_' + timestamp_str + '.xml'
        http_get2file(url, settings.ccbapi.username, settings.ccbapi.password, filename=filename)
        trace("Emitted XML file '" + filename + "'")

    trace("DONE!", banner=True)

    sys.stdout.flush()
    sys.stderr.flush()


def http_get2file(url, username, password, filename=None):
    if not filename:
        with tempfile.NamedTemporaryFile(delete=False) as temp:
            filename = temp.name
            temp.close()
    with open(filename, 'wb') as file_w:
        c = pycurl.Curl()
        c.setopt(c.URL, url)
        c.setopt(c.USERPWD, username + ':' + password)
        c.setopt(c.WRITEDATA, file_w)
        c.perform()
        c.close()
        file_w.close()
    return filename


def trace(msg_str, banner=False):
    global g
    if g.trace_flag:
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
