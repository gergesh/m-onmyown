#!/usr/bin/env python3
# coding=utf8

from __future__ import print_function
import requests
from docx.api import Document
import os
import tempfile
from sys import exit
from datetime import date, timedelta
import re

DOMAIN = 'http://m-ontv.net'
MOSAD = 288
CLASS = 'יב 4'

# find table
ontv = requests.get('{}/indexEmbed.asp?theMosad={}&theIndex=index1'.format(DOMAIN, MOSAD)).text
page = requests.get('{}/loadMessagesAjax.asp?themosad={}&screen=2&side=both&displayMode=static'.format(DOMAIN, MOSAD)).text
fileID = re.search(r'data-fileID="(\d+)"', page).group(1)
docx_filename = requests.get('{}/getFileMessageDetailsAjax.asp?fileID={}'.format(DOMAIN, fileID)).text
docx_url = DOMAIN + '/' + docx_filename[:docx_filename.find(',')].replace('\\', '/')
# feed to docxlib
tf, fn = tempfile.mkstemp()
os.write(tf, requests.get(docx_url).content)
doc = Document(fn)
title = doc.paragraphs[0].text.strip()
tomorrow = date.today() + timedelta(days=1)
if title[title.rfind(' ')+1:] != tomorrow.strftime('%-d.%-m.%y'):
    print('טבלה לא מעודכנת')
    exit(1)
table = doc.tables[0]

# find class
row = None
for r in table.rows:
    if r.cells[0].text == CLASS:
	    row = r
	    break
else:
    print('Illegal class chosen.')
    exit(2)

print(title)
# parse changes
changes = [c.text for c in row.cells]
for i, cell in enumerate(changes[1:]):
    if cell == changes[i-1]:
        continue
    end_hr = i
    while end_hr + 1 < len(changes) and changes[end_hr+1] == changes[i]:
        end_hr += 1
    #print('Hours {}-{}: {}'.format(i, end_hr, cell))

    if cell == '':
        outstr = 'כרגיל'
    elif all(x == '/' for x in cell):
        outstr = 'פוצץ'
    else:
        outstr = cell
    print('שעות {}-{} {}'.format(i, end_hr, outstr))
