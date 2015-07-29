#!/Library/Frameworks/Python.framework/Versions/2.7/bin/python

import sys, getopt, os.path, csv, argparse, petl

def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument("--individual-filename", required=True, nargs='+', action='append', \
        help="'Individual' filename (input CSV file)")
    parser.add_argument("--individual-id-fieldname", help="'Individual' ID fieldname", default="Individual ID")
    parser.add_argument("--family-filename", required=True, nargs='+', action='append', \
        help="'Family' filename (input CSV file)")
    parser.add_argument("--contribution-filename", required=True, nargs='+', action='append', \
        help="'Contribution' filename (input CSV file)")
    parser.add_argument("--output-filename", required=True, help="'Output' filename (output XLS file)")
    args = parser.parse_args()

    individual_table = join_tables(args.individual_filename[0], args.individual_id_fieldname)
    print individual_table

def join_tables(filename_list, id_fieldname):
    curr_table = None
    for filename in filename_list:
        if not os.path.isfile(filename):
            print "Error: cannot open file '" + filename + "'"
        else:
            next_table = petl.fromcsv(filename)
            header_row = petl.fieldnames(next_table)
            if id_fieldname is not None and id_fieldname not in header_row:
                print "Error: " + str(header_row) + " header row does not contain required ID field named '" + \
                    id_fieldname + "'"
            else:
                if curr_table is not None:
                    print curr_table
                    print next_table
                    curr_table = petl.outerjoin(curr_table, next_table, key=id_fieldname)
                else:
                    curr_table = next_table
    return curr_table

def csvs2dictlist(filename_array, id_fieldname):
    dictlist = []
    for filename in filename_array:
        if os.path.isfile(filename):
            with open(filename) as csvfile:
                csv_dict_reader = csv.DictReader(csvfile)
                for row in csv_dict_reader:
                    dictlist.append(row)
            print str(dictlist)
            return dictlist
        else:
            print "Error: cannot open " + filename

def csvs2listlist(filename_array, id_fieldname=None):

    individual_rowset = RowSet(id_fieldname, *filename_array)
#    test1_rowset = RowSet(None, 'a', 'b')
#    test2_rowset = RowSet()

    listlist = []
    for filename in filename_array:
        if os.path.isfile(filename):
            with open(filename) as csvfile:
                row_num = 1
                header_count = -1
                csv_reader = csv.reader(csvfile)
                for row in csv_reader:
                    if header_count == -1:
                        header_count = len(row)
                        if id_fieldname is not None and id_fieldname not in row:
                            print "Error: " + str(row) + " header row does not contain required ID field named '" + \
                                id_fieldname + "'"
                    elif len(row) != header_count:
                        print "Error: header has " + str(header_count) + " fields, but row #" + str(row_num) + \
                            " has " + str(len(row)) + " fields"
                    listlist.append(row)
                    row_num += 1
            print str(listlist)
        else:
            print "Error: cannot open file '" + filename + "'"
    return listlist

if __name__ == "__main__":
    main(sys.argv[1:])
