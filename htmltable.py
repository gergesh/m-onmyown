# -*- coding: utf-8 -*-
"""
A script written by Yoav Shai.
You can use -c, -a and -t at launch to specify classroom, use ascii-compliant and translation modes respectively.
My goal with this is to have a program that can fetch your schedule changes.
Automate this to run at ~6PM every day and you'll live a good life.

NOTE: This was my first ever python script. It's bloated and it's shit. It's also unmaintained since we switched to docx.
"""
import requests  # used for getting the current timetable.
import sys  # used for exiting the program when users are dumb.
import pandas as pd  # used for the dataframe type.
from bs4 import BeautifulSoup  # used to parse the html table.
import re  # used for finding the numbers in the inputted classroom string and removing newlines.
import argparse

hours_count = 9  # number of hours per day (in the table) # could easily be dynamic, I was lazy back then.

class html_table(object):
    def __init__(self, url):
        self.url = url
        self.r = requests.get(self.url)
        self.url_soup = BeautifulSoup(self.r.content, "lxml")
        self.title = self.url_soup.find("p", {'class': 'MsoNormal'}).text
        self.table = self.url_soup.find("table")

    def read(self):
        """ Reads the timetable to a dataframe. """
        n_rows = len(self.table.find_all("tr"))
        n_cols = hours_count + 1  # leaving one cell for the classroom name

        # <colspan> - how many columns I'm occupying, including myself, going to the left.
        # <rowspan> - how many rows I'm occupying, including myself, going downwards.

        # Create dataframe with the same number of rows and columns as the timetable.
        df = pd.DataFrame(index=range(0, n_rows), columns=range(0, n_cols))

        ignore_list = set()  # set - an unordered list

        # Start by iterating over each row in this table...
        row_index = 0
        cellcount = 0
        for row in self.table.find_all("tr"):

            col_index = 0
            for cell in row.find_all(["td", "th"]):

                cellcount += 1
                while '[' + str(col_index) + '][' + str(row_index) + ']' in ignore_list:
                    if col_index == hours_count:
                        col_index = 0
                        row_index += 1
                    else:
                        col_index += 1

                if cell.get("colspan") is None:
                    colspan = 1
                else:
                    colspan = int(cell.get("colspan"))

                if cell.get("rowspan") is None:
                    rowspan = 1
                else:
                    rowspan = int(cell.get("rowspan"))

                for i in range(rowspan):
                    for j in range(colspan):
                        ignore_list.add('[' + str(col_index + j) + '][' + str(row_index + i) + ']')
                        df[col_index + j][row_index + i] = cell.get_text()

            row_index += 1

        # Return dataframe
        return df


grade = {
    'y': u'י',
    'ya': u'יא',
    'yb': u'יב',
    u'י': u'י',
    u'יא': u'יא',
    u'יב': u'יב'
}  # dictionary used to convert the inputted letters to grades, used by to_classroom(s)


# used to convert inputted strings to classrooms.
def to_classroom(s):
    """ Converts the user's input to a classroom that can be found in the table. """
    s = s.decode("utf8")
    if len(re.findall(r'\d+', s)) == 1:
        number = re.findall(r'\d+', s)[0]
    else:
        number = '9001'  # won't find it later

    letters = s.replace(number, '').replace(' ', '').replace('"', '').replace("'", '')  # letters only hopefully
    if letters in grade:
        return grade[letters] + ' ' + number
    else:
        return "classroom_illegal"  # won't be able to find it later, will notify the user


def purify(s):
    """ Removes newlines and other shenanigans from the strings before we display them
    to the user """
    return re.sub(r'\r', r'', re.sub(' +', ' ', re.sub(r'\r\n', ' ', s))).strip()


def gtrans(s):
    return translator.translate(s, src="iw", dest="en").text


parser = argparse.ArgumentParser(description='A script that fetches your schedule changes from the realit website')
parser.add_argument('-c', '--classroom', help='Specify your classroom before execution.')
parser.add_argument('-a', '--ascii', help='Turn on ASCII mode, for usage in non-unicode environments.',
                    action='store_true')
parser.add_argument('-t', '--translate',
                    help='Turn on translation mode for the changes strings, only works when also using ASCII mode.',
                    action='store_true')  # not working properly - not my fault
parser.add_argument('--force-unicode', help='Disables the unicode support check.', action='store_true')
args = parser.parse_args()
classroom, ascii_mode, translate_mode, force_unicode = args.classroom, args.ascii, args.translate, args.force_unicode

if not ascii_mode and not force_unicode:
    try:
        u'שלום'.encode(sys.stdout.encoding)
    except UnicodeEncodeError or UnicodeDecodeError:
        print "It appears that your execution environment does not support hebrew characters, turning ASCII mode on" \
              "for you. If you think this is a mistake, use --force-unicode at launch."
        ascii_mode = True

if translate_mode and not ascii_mode:
    print "You cannot use translation services when running outside of ASCII mode. Turning them off now."
    translate_mode = False

if translate_mode:
    from googletrans import Translator

    translator = Translator()

canceled_strs = set(
    [u'\n' + i * '/' + '\n' for i in
     range(4, 11)])  # this string will appear in a cell when the lesson has been canceled.
empty_str = u'\n\xa0\n'  # this string will appear in a cell when there are no changes for that period.

response = requests.get(  # this request is used to retrieve the file id.
    "http://m-ontv.net/loadMessagesAjax.asp?themosad=288&screen=2&side=both&displayMode=static&mm=1").content
file_id = response[response.find('data-fileID="') + 13:response.find('"', response.find('data-fileID="') + 13)]
# file id starts after the 'data-fileID=' text and ends with the closest quotation marks after it.

# now we will craft a request using the file ID to get the file name.
response = requests.get("http://m-ontv.net/getFileMessageDetailsAjax.asp?fileID=" + file_id).content
# we got it! crafting the html table's url in the next line
changes_url = "http://m-ontv.net/files/288/" + response[10:-12]
print "\n" + changes_url + "\n"

# let's locate the dude's classroom. he deserves it.
if classroom is None:  # if the classroom wasn't inputted as an argument.
    if ascii_mode:
        classroom = to_classroom(raw_input("I'm proud to be a member of ").decode(sys.stdin.encoding).encode("utf8"))
    else:
        classroom = to_classroom(raw_input("אני בכיתה ").decode(sys.stdin.encoding).encode("utf8"))
else:
    classroom = to_classroom(classroom.decode(sys.stdin.encoding).encode("utf8"))

if ascii_mode:
    print '\nSchedule changes for', html_table(changes_url).title[
                                    re.search("\d", html_table(changes_url).title).start():][:-1] + ':'  # date only
else:
    print '\n' + purify(html_table(changes_url).title) + ':'
table = html_table(changes_url).read()

classroom_row = -1
for j in range(2, len(table)):  # first two rows are the time and period lines, no need to look through them.
    table[0][j] = table[0][j].strip()  # remove the newlines.
    if table[0][j] == classroom:
        classroom_row = j
        # print "\nClassroom found!\n"
        break

if classroom_row == -1:
    print "Couldn't locate your classroom, odd. Have you tried turning it off and on again?"
    sys.exit()

# let's print his changes for the day!
curr_hour = 1
while curr_hour <= hours_count:
    if table[curr_hour][classroom_row] == empty_str or (
            isinstance(table[curr_hour][classroom_row], float)):  # no change
        j = 0
        while curr_hour + j < hours_count and (table[curr_hour + j + 1][classroom_row] == empty_str or isinstance(
                table[curr_hour + j + 1][classroom_row], float)):
            j += 1

        # now let's print the unchanged hours to the user
        if ascii_mode:
            if j == 0:
                print "Lesson number %d is unchanged." % curr_hour
            else:
                print "Lessons %d-%d are unchanged." % (curr_hour, curr_hour + j)
        else:
            if j == 0:
                print u"בשעה מספר " + str(curr_hour) + u" אין שינויי מערכת."
            else:
                print u"בשעות מספר " + str(curr_hour) + u" עד " + str(curr_hour + j) + u" אין שינויי מערכת."
        curr_hour += j

    elif table[curr_hour][classroom_row] in canceled_strs:
        j = 0
        while curr_hour + j < hours_count and table[curr_hour + j + 1][classroom_row] in canceled_strs:
            j += 1
        if ascii_mode:
            if j == 0:
                print "Lesson number %d has been canceled." % curr_hour
            else:
                print "Lessons %d-%d have been canceled." % (curr_hour, curr_hour + j)
        else:
            if j == 0:
                print u"שעה מספר " + str(curr_hour) + u" בוטלה."
            else:
                print u"שעות מספר " + str(curr_hour) + u" עד " + str(curr_hour + j) + u" בוטלו."
        curr_hour += j

    else:  # schedule changes
        j = 0
        while curr_hour + j < hours_count and table[curr_hour][classroom_row] == table[curr_hour + j + 1][
                    classroom_row]:
            j += 1

        # now we shall print the schedule changes
        if ascii_mode and translate_mode:
            if j == 0:
                print "At lesson number %d %s." % (curr_hour, gtrans(purify(table[curr_hour][classroom_row])))
            else:
                print "At lessons %d-%d %s." % (
                    curr_hour, curr_hour + j, gtrans(purify(table[curr_hour][classroom_row])))
        elif ascii_mode:
            if j == 0:
                print "Lesson number %d has changed." % curr_hour
            else:
                print "Lessons %d-%d have changed." % (curr_hour, curr_hour + j)
        else:
            if j == 0:
                print u"בשעה מספר " + str(curr_hour) + ' ' + purify(table[curr_hour][classroom_row]) + '.'
            else:
                print u"בשעות מספר " + str(curr_hour) + u" עד " + str(curr_hour + j) + ' ' + purify(
                    table[curr_hour][classroom_row]) + '.'
        curr_hour += j

    curr_hour += 1
