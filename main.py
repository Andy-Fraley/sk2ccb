#!/usr/bin/python

import sys, getopt

def usage():
        print 'Usage: convert.py --individual-filename <individual_filename> --family-filename <family_filename>\n'\
              '    --contribution-filename <contribution_filename> --output-filename <output_filename>\n\n'\
              '    where\n\n'\
              '        <individual_filename> is a CSV file extract from Servant Keeper containing one line per '\
              'individual\n\n'\
              '        <family_filename> is a CSV file extract from Servant Keeper containing one line per '\
              'family\n\n'\
              '        <contribution_filename> is a CSV file extract from Servant Keeper containing one line per '\
              'contribution\n\n'\
              '        <output_filename> is the transformed output Excel loading file for CCB\n\n'\
              '    NOTE: There must be at least one each individual_file, family_file, and contribution_file as \n'\
              '    input files.  However, contents for individuals, familys, and contributions can be split across\n'\
              '    multiple files each like:\n\n'\
              '        ./main.py --individual_file indiv1.csv --individual_file indiv2.csv --family_file fam.csv\n'\
              '            --contribution_file contrib.csv\n\n'\
              '    Multiple files per object type will work so long as (1) each row has the ID column for the\n'\
              '    object type and (2) there are no duplicate columns for any given object ID.'

def main(argv):
    individual_filenames = []
    family_filenames = []
    contribution_filenames = []
    output_filename = ''

    try:
        opts, args = getopt.getopt(argv,"",["individual-filename=","family-filename=","contribution-filename=",\
                                            "output-filename=","help"])

    except getopt.GetoptError:
        usage()
        sys.exit(2)

    for opt, arg in opts:
        if opt == '--help':
            usage()
            sys.exit()

        elif opt in ("--individual-filename"):
            individual_file = arg
            individual_filenames.append(arg)

        elif opt in ("--family-filename"):
            family_file = arg
            family_filenames.append(arg)

        elif opt in ("--contribution-filename"):
            contribution_file = arg
            contribution_filenames.append(arg)

        elif opt in ("--output-filename"):
            output_filename = arg

    if len(individual_filenames) == 0 or len(family_filenames) == 0 or len(contribution_filenames) == 0 \
       or output_filename == '':
        usage()
        sys.exit(2)

    print 'Individual filename(s): ' + str(individual_filenames)
    print 'Family filename(s): ' + str(family_filenames)
    print 'Contribution filename(s): ' + str(contribution_filenames)
    print 'Output file is "' + output_filename + '"'

if __name__ == "__main__":
    main(sys.argv[1:])
