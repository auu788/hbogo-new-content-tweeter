#!/usr/bin/python
# -*- coding: utf-8 -*-

import sqlite3
import requests
import time
import configparser
import hbogo
import argparse
import os

# Content type
# 7 - Episode [?]
# 5 - Season
# 3 - Episode
# 2 - Series
# 1 - Movie

config = configparser.ConfigParser()
config.read('config.ini')

DB_FILE = config['Config']['DatabaseFile']

SITEMAP_URL = "http://plapi.hbogo.eu/v5/SiteMap/JSON/POL/COMP"
CONTENT_URL = "http://plapi.hbogo.eu/player50.svc/Content/JSON/POL/COMP/"
HBOGO_URL = "hbogo.pl/"

parser = argparse.ArgumentParser(description='Get polish HBO Go  data content and tweet about new things.')
parser.add_argument('--init', '-i', action='store_true', help='creates fresh DB')
parser.add_argument('--tweet', '-t', action='store_true', help='tweets about changes in DB')

args = parser.parse_args()
if args.init:
    hbogo.createContentDB()
    print ('Creating new DB done.')
    exit()

if not os.path.isfile(DB_FILE):
    print ('There is no DB file, try again: python3 {} --init'.format(os.path.basename(__file__)))
    exit()

if args.tweet:
    print ("Twwete")
    hbogo.POST_TWEETS = True

try:
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    movies_db = c.execute("SELECT * FROM hbogo_content WHERE content_type=1").fetchall()
    series_db = c.execute("SELECT * FROM hbogo_content WHERE content_type=2").fetchall()
except:
    print ('DB is unfinished, try again: python3 {} --init'.format(os.path.basename(__file__)))
    exit()

#data_api = hbogo.getAPIData()

print ("Updating ID base...")
data = hbogo.checkTypes()

upcomings_db = c.execute("SELECT * FROM hbogo_content WHERE is_upcoming=1").fetchall()

print ("Checking upcoming releases: " + str(len(upcomings_db)))
for item in upcomings_db:
    id = item['id']
    content_type = item['content_type']

    item_content = requests.get(CONTENT_URL + id).json()

    # Zoptymalizowanie ilości linijek kodu
    if content_type == 1:
        if item_content['IsUpcoming'] == 0:
            print ("Premiere: " + item['title'])
            hbogo.postOnTwitter(item_content, False, 0, False)
            c.execute("UPDATE hbogo_content SET is_upcoming=? WHERE id=?", (0, id))
            conn.commit()
    else:
        if item_content['Parent']['IsUpcoming'] == 0:
            print ("Premiere: " + item['title'])
            hbogo.postOnTwitter(item_content, False, 0, False)
            c.execute("UPDATE hbogo_content SET is_upcoming=? WHERE id=?", (0, id))
            conn.commit()

cnt = 1
total = len(data)

print ("Comparing ID DB with Content DB...")
for item in data:
    id = item['id']
    content_type = item['content_type']

    if item['is_removed'] == 1:
        is_rem = c.execute("SELECT is_removed FROM hbogo_content WHERE id=?", (id,)).fetchone()
        if is_rem[0] == 0:
            c.execute("UPDATE hbogo_content SET is_removed=? WHERE id=?", (1, id))
            data = c.execute("SELECT id, title, year, content_type, seasons FROM hbogo_content WHERE id=?", (id,)).fetchone()
            conn.commit()
            print ('Removed: ' + id)
        else:
            continue
            #hbogo.postOnTwitter(data, False, 0, True)

    if cnt % 100 == 0:
        print ('{}/{}'.format(cnt, total))

    if content_type == 1:
        if not any(id in sub for sub in movies_db):
            item_content = requests.get(CONTENT_URL + id).json()
            print ('New movie: ' + item_content['EditedName'] + ' --- ' + id)
            hbogo.addItemToDB(item_content)

    else:
        item_content = requests.get(CONTENT_URL + id).json()

        if not any(id in sub for sub in series_db):
            print ('New series: ' + item_content['Parent']['EditedName'] + ' --- ' + id)
            hbogo.addItemToDB(item_content)

        else:
            id = item_content['Parent']['Id']
            seasons_db_cnt = c.execute("SELECT seasons FROM hbogo_content WHERE id=?", (id,)).fetchone()
            seasons_api_cnt = len(item_content['Parent']['ChildContents']['Items'])
            delta = (seasons_api_cnt - seasons_db_cnt[0])

            if delta != 0:
                c.execute("UPDATE hbogo_content SET seasons=? WHERE id=?", (seasons_api_cnt, id))
                conn.commit()
                hbogo.postOnTwitter(item_content, True, delta, False)
                print ("No. of seasons changed: " + item_content['Parent']['EditedName'] + ' [' + str(seasons_db_cnt[0]) + ' -> ' + str(seasons_api_cnt) + ']')
    cnt += 1

conn.close()
