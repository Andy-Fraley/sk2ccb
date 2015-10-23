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

    worship_services = {
        '8am': [7, ['08:00:00']],
        '9am': [8, ['09:00:00']],
        '10am': [9, ['10:00:00']],
        '1115am': [10, ['11:15:00']],
        'ChristmasEve': [13, ['16:00:00', '19:00:00', '23:00:00']]
    }

    parser = argparse.ArgumentParser(description="Dumps attendance info across a range of worship events")
    parser.add_argument("--worship-services", required=True, nargs='*', default=argparse.SUPPRESS, \
        help="One or more of " + ', '.join(worship_services.keys()))
    parser.add_argument("--start-date", required=True, help="Start date")
    parser.add_argument("--end-date", required=True, help="End date")
    parser.add_argument('--trace', action='store_true', help="If specified, prints trace output to stdout.")
    args = parser.parse_args()

    g.trace_flag = args.trace

    start_date = parse_date(args.start_date)
    end_date = parse_date(args.end_date)
    if start_date > end_date:
        raise Exception("End Date must follow Start Date")

    christmaseve_services_info = None
    sunday_services_info = None
    for worship_service in args.worship_services:
        assert worship_service in worship_services, "No such worship service '" + worship_service + \
            "' to dump from CCB."
        if worship_service == 'ChristmasEve':
            christmaseve_services_info = worship_services[worship_service]
        else:
            if not sunday_services_info:
                sunday_services_info = []
            sunday_services_info.append(worship_services[worship_service])

    # Step weekly from start_date to end_date for Sunday worship services
    if sunday_services_info:
        current_date = start_date
        while (current_date <= end_date):
            for services_info in sunday_services_info:
                retrieve_services_info(current_date, services_info)
            current_date += datetime.timedelta(days=7)

    # Step thru ChristmasEve dates between start_date and end_date
    if christmaseve_services_info:
        if start_date.month == 12 and start_date.day > 24:
            start_year = start_date.year + 1
        else:
            start_year = start_date.year
        current_date = datetime.date(start_year, 12, 24)
        while (current_date <= end_date):
            retrieve_services_info(current_date, christmaseve_services_info)
            current_date = current_date.replace(year = current_date.year + 1)

    trace("DONE!", banner=True)

    sys.stdout.flush()
    sys.stderr.flush()


def print_file(filename):
    with open(filename, 'r') as f:
            print f.read()


def delete_file(filename):
    os.remove(filename)


def retrieve_services_info(date, services_info):
    event_id = services_info[0]
    for service_time in services_info[1]:
        filename = retrieve_service_info(date, event_id, service_time)
        print_file(filename)
        delete_file(filename)


def retrieve_service_info(date, event_id, service_time):
    opt_str = '&id=' + str(event_id) + '&occurrence=' + str(date) + '+' + str(service_time)
    url = 'https://ingomar.ccbchurch.com/api.php?srv=attendance_profile' + opt_str
    trace('XML attendance data for ' + opt_str, banner=True)
    return http_get2file(url, settings.ccbapi.username, settings.ccbapi.password)


def parse_date(s):
    try:
        date = datetime.datetime.strptime(s, '%Y%m%d').date()
    except ValueError:
        raise ValueError('Invalid date: ' + s)
    except:
        raise

    return date


def date_format(date):
    return str(date.year) + str(date.month) + str(date.day)


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
