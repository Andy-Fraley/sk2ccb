#!/usr/bin/python

import sys, getopt

def usage():
        print 'Usage: convert.py --individual-file <individual_file> --family-file <family_file>\n'\
              '    --contribution-file <contribution_file> --output-file <output_file>\n\n'\
              '    where\n\n'\
              '        <individual_file> is a CSV file extract from Servant Keeper containing one line per '\
              'individual\n\n'\
              '        <family_file> is a CSV file extract from Servant Keeper containing one line per '\
              'family\n\n'\
              '        <contribution_file> is a CSV file extract from Servant Keeper containing one line per '\
              'contribution\n\n'\
              '        <output_file> is the transformed output Excel loading file for CCB\n\n'\
              '    NOTE: There must be at least one each individual_file, family_file, and contribution_file as \n'\
              '    input files.  However, contents for individuals, familys, and contributions can be split across\n'\
              '    multiple files each like:\n\n'\
              '        ./main.py --individual_file indiv1.csv --individual_file indiv2.csv --family_file fam.csv\n'\
              '            --contribution_file contrib.csv\n\n'\
              '    Multiple files per object type will work so long as (1) each row has the ID column for the\n'\
              '    object type and (2) there are no duplicate columns for any given object ID.'

def main(argv):
    individual_file = ''
    family_file = ''
    contribution_file = ''
    output_file = ''

    try:
        opts, args = getopt.getopt(argv,"",["individual-file=","family-file=","contribution-file=","output-file=","help"])

    except getopt.GetoptError:
        usage()
        sys.exit(2)

    for opt, arg in opts:
        if opt == '--help':
            usage()
            sys.exit()

        elif opt in ("--individual-file"):
            individual_file = arg

        elif opt in ("--family-file"):
            family_file = arg

        elif opt in ("--contribution-file"):
            contribution_file = arg

        elif opt in ("--output-file"):
            output_file = arg

    if individual_file == '' or family_file == '' or contribution_file == '' or output_file == '':
        usage()
        sys.exit(2)

    print 'Individual file is "' + individual_file + '"'
    print 'Family file is "' + family_file + '"'
    print 'Contribution file is "' + contribution_file + '"'
    print 'Output file is "' + output_file + '"'

if __name__ == "__main__":
    main(sys.argv[1:])
