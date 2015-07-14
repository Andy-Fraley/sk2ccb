import os.path, csv

# A RowSet accumulates rows across one or more CSV files.  If >1 CSV files, then there must be a common
# ID field used to stitch multiple RowSet's back into one
class RowSet:

    def __init__(self, id_fieldname=None, *filename_list):
        self.id_fieldname = id_fieldname
        self.error_list = []
        self.data_rows = []
        self.header_row = None

        len_filename_list = len(self.filename_list)

        if len_filename_list < 1:
            raise RowSetError('A RowSet must be created from at least one CSV file')

        elif len_filename_list == 1:
            filename=filename_list[0]
            if os.path.isfile(filename):
                with open(filename) as csvfile:
                    row_num = 1
                    header_count = -1
                    csv_reader = csv.reader(csvfile)
                    for row in csv_reader:
                        if header_count == -1:
                            header_count = len(row)
                            if id_fieldname is not None and id_fieldname not in row:
                                self.error_list.append(str(row) + \
                                                       " header row does not contain required ID field named '" + \
                                                       id_fieldname + "'", filename)
                            header_row = row
                        elif len(row) != header_count:
                            self.error_list.append("Header has " + str(header_count) + \
                                                   " fields, but row #" + \
                                                   str(row_num) + " has " + str(len(row)) + \
                                                   " fields")
                        self.data_rows.append(row)
                        row_num += 1
            else:
                self.error_list.append("Cannot open CSV input file '" + filename + "'")

        elif len_filename_list > 1:
            if self.id_fieldname is None:
                raise RowSetError('If a RowSet is constructed from multiple CSV files, a joining ID fieldname ' \
                                  'must be specified')
            for filename in filename_list:
                self.merge(RowSet(id_fieldname, filename))

    def merge(self, RowSet rowset):
        pass
