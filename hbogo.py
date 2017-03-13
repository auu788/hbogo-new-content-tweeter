#!/usr/bin/python
# -*- coding: utf-8 -*-

import requests
import configparser
import sqlite3
from twython import Twython
from urllib.request import urlopen
import os

config = configparser.ConfigParser()
config.read('config.ini')

DB_FILE = config['Config']['DatabaseFile']

SITEMAP_URL = "http://plapi.hbogo.eu/v5/SiteMap/JSON/POL/COMP"
CONTENT_URL = "http://plapi.hbogo.eu/player50.svc/Content/JSON/POL/COMP/"
HBOGO_URL = "hbogo.pl/redirect/"

POST_TWEETS = config['Config']['PostTweets']

APP_KEY = config['Config']['AppKey']
APP_SECRET = config['Config']['AppSecret']
OAUTH_TOKEN = config['Config']['OAuthToken']
OAUTH_TOKEN_SECRET = config['Config']['OAuthTokenSecret']

def prepareMsg(item, isChangedSeason, delta, isDeleted):
    if isChangedSeason == False and isDeleted == False:
        if item['ContentType'] == 1:
            if item['ImdbRate'] != 0:
                imdb_msg = ', IMDB: ' + str(item['ImdbRate'])
            else:
                imdb_msg = ''

            if item['ProductionYear'] != 0:
                year_msg = ' [' + str(item['ProductionYear']) + ']'
            else:
                year_msg = ''

            url_msg = ' ' + HBOGO_URL + str(item['ExternalId'])
            msg = 'Dodano film ' + item['EditedName'] + year_msg + imdb_msg + url_msg + ' #HBOGo'

        else:
            if item['Parent']['ImdbRate'] != 0:
                imdb_msg = ', IMDB: ' + str(item['Parent']['ImdbRate'])
            else:
                imdb_msg = ''

            if item['Parent']['ProductionYear'] != 0:
                year_msg = ' [' + str(item['Parent']['ProductionYear']) + ']'
            else:
                year_msg = ''

            seasons = len(item['Parent']['ChildContents']['Items'])
            if seasons == 1:
                seasons_msg = " sezon"
            elif seasons > 1 and seasons < 5:
                seasons_msg = " sezony"
            else:
                seasons_msg = " sezonów"

            url_msg = ' ' + HBOGO_URL + str(item['Parent']['ExternalId'])

            msg = 'Dodano serial ' + item['Parent']['EditedName'] + year_msg + ' [' + str(seasons) + seasons_msg + ']' + imdb_msg + url_msg + ' #HBOGo'

    elif isDeleted == True:
        if item['year'] != 0:
            year_msg = ' [' + str(item['year']) + ']'
        else:
            year_msg = ''

        if item['content_type'] == 1:
            msg = 'Usunięto film ' + item['title'] + year_msg + '. #HBOGo'

        else:
            seasons = item['seasons']

            if seasons == 1:
                seasons_msg = " sezon"
            elif seasons > 1 and seasons < 5:
                seasons_msg = " sezony"
            else:
                seasons_msg = " sezonów"

            msg = 'Usunięto serial ' + item['title'] + year_msg + ' [' + str(seasons) + seasons_msg + ']. #HBOGo'

    elif isChangedSeason == True:
        if abs(delta) == 1:
            seasons_msg = " sezon"
        elif abs(delta) > 1 and abs(delta) < 5:
            seasons_msg = " sezony"
        else:
            seasons_msg = " sezonów"

        if delta > 0:
            msg = 'Dodano ' + str(delta) + seasons_msg + ' serialu ' + item['Parent']['EditedName'] + ' [teraz jest ich: ' + str(len(item['Parent']['ChildContents']['Items'])) + ']. #HBOGo'

        elif delta < 0:
            delta = abs(delta)
            msg = 'Usunięto ' + str(delta) + seasons_msg + ' serialu ' + item['Parent']['EditedName'] + ' [teraz jest ich: ' + str(len(item['Parent']['ChildContents']['Items'])) + ']. #HBOGo'

    return msg

def postOnTwitter(item, isChangedSeason, delta, isDeleted):
    if POST_TWEETS == "False":
        print ("TWETET")
        return

    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    if isDeleted == True:
        id = item['id']
    else:
        if item['ContentType'] == 1:
            id = item['Id']
        else:
            id = item['Parent']['Id']

    img_url = c.execute("SELECT img_url FROM hbogo_content WHERE id=?", (id,)).fetchone()
    c.close()

    msg = prepareMsg(item, isChangedSeason, delta, isDeleted)

    twitter = Twython(APP_KEY, APP_SECRET, OAUTH_TOKEN, OAUTH_TOKEN_SECRET)

    img = urlopen(img_url[0])
    response = twitter.upload_media(media=img)

    try:
        twitter.update_status(status=msg, media_ids=[response['media_id']])
    except TypeError:
        twitter.update_status(status=msg)
    except:
        msg = msg[:-15]
        twitter.update_status(status=msg, media_ids=[response['media_id']])

    print ("Created tweet: " + msg)


def addItemToDB(item):
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    if item['ContentType'] == 1:
        id = item['Id']
        img_url = item['BackgroundUrl']
        title = item.get('EditedName')
        original_title = item['OriginalName']
        availability_from = item['AvailabilityFrom']
        availability_to = item['AvailabilityTo']
        is_upcoming = item['IsUpcoming']
        content_type = item['ContentType']
        year = item['ProductionYear']
        imdb_rating = item['ImdbRate']
        url = HBOGO_URL + item['ExternalId']
        seasons = None

    else:
        id = item['Parent']['Id']
        img_url = item['Parent']['BackgroundUrl']
        title = item['Parent']['EditedName']
        original_title = item['Parent']['OriginalName']
        availability_from = item['Parent']['AvailabilityFrom']
        availability_to = item['Parent']['AvailabilityTo']
        is_upcoming = item['Parent']['IsUpcoming']
        content_type = item['Parent']['ContentType']
        year = item['Parent']['ProductionYear']
        imdb_rating = item['Parent']['ImdbRate']
        url = HBOGO_URL + item['Parent']['ExternalId']
        seasons = len(item['Parent']['ChildContents']['Items'])


    c.execute("INSERT INTO hbogo_content VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);", (id, title, original_title, year, content_type, seasons, imdb_rating, url, img_url, availability_from, availability_to, is_upcoming, 0))
    conn.commit()
    print ('Added to DB: ' + title)

    if is_upcoming == False:
        postOnTwitter(item, False, 0, False)

    conn.close()

def getAPIData():
    data = requests.get(SITEMAP_URL).json()

    return data

def checkTypes():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    data_db = c.execute("SELECT * FROM hbogo_types").fetchall()
    data_api = getAPIData()
    combined = str(data_api)

    if len(data_api["Items"]) < 100:
        exit();

    for item_db in data_db:
        id = item_db['id']

        if id not in combined:
            is_rem = c.execute("SELECT is_removed FROM hbogo_types WHERE id=?", (id,)).fetchone()
            if is_rem['is_removed'] == 0:
                c.execute("UPDATE hbogo_types SET is_removed=? WHERE id=?", (1, id))
                conn.commit()
                print ("Removed ID: " + id)

    for item_api in data_api['Items']:
        if item_api['Duration'] != None:
            id = item_api['Url'][-36:]

            if not any(id in x for x in data_db):
                item_content = requests.get(CONTENT_URL + id).json()

                if item_content['SEOUrl'][10:].replace('&', '') != item_api['SeoFriendlyUrl'][10:]:
                    content_type = 2
                else:
                    content_type = item_content['ContentType']

                c.execute("INSERT INTO hbogo_types VALUES (?, ?, ?)", (id, content_type, 0))
                conn.commit()
                print ("Added ID: " + id)

    ready_data = c.execute("SELECT * FROM hbogo_types WHERE content_type=2 OR content_type=1").fetchall()
    conn.close()
    return ready_data

def createTypesDB():
    if os.path.isfile(DB_FILE):
        os.remove(DB_FILE)

    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS hbogo_types (id TEXT, content_type INTEGER, is_removed INTEGER)''')
    conn.commit()

    data = getAPIData()
    cnt = 1
    total = len(data['Items'])

    for item in data['Items']:
        if item['Duration'] != None:
            id = item['Url'][-36:]
            data_content = requests.get(CONTENT_URL + id).json()

            try:
                if data_content['SEOUrl'][10:].replace('&', '') != item['SeoFriendlyUrl'][10:]:
                    content_type = 2
                else:
                    content_type = data_content['ContentType']
            except:
                print (data_content['Id'])

            print ('{}/{}: {} --- {}'.format(cnt, total, data_content.get('EditedName'), content_type))
            cnt += 1
            c.execute("INSERT INTO hbogo_types VALUES (?, ?, ?)", (id, content_type, 0,))
            conn.commit()

    conn.close()

def createContentDB():
    #createTypesDB()

    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS hbogo_content
                 (id TEXT, title TEXT, original_title TEXT, year INTEGER, content_type INTEGER, seasons INTEGER, imdb_rating DECIMAL, url TEXT, img_url TEXT, availability_from TEXT, availability_to TEXT, is_upcoming INTEGER, is_removed INTEGER)''')
    conn.commit()

    id_data = c.execute("SELECT id, content_type FROM hbogo_types WHERE content_type=2 OR content_type=1").fetchall()

    cnt = 1

    total_cnt = len(id_data)
    for item in id_data:
        id = item['id']
        data_content = requests.get(CONTENT_URL + id).json()

        if item['content_type'] == 1:
            title = data_content.get('EditedName')
            original_title = data_content['OriginalName']
            availability_from = data_content['AvailabilityFrom']
            availability_to = data_content['AvailabilityTo']
            is_upcoming = data_content['IsUpcoming']
            content_type = data_content['ContentType']
            year = data_content['ProductionYear']
            imdb_rating = data_content['ImdbRate']
            url = HBOGO_URL + str(data_content['ExternalId'])
            seasons = None
            img_url = data_content['BackgroundUrl']

        else:
            title = data_content['Parent']['EditedName']
            original_title = data_content['Parent']['OriginalName']
            availability_from = data_content['Parent']['AvailabilityFrom']
            availability_to = data_content['Parent']['AvailabilityTo']
            is_upcoming = data_content['Parent']['IsUpcoming']
            content_type = data_content['Parent']['ContentType']
            year = data_content['Parent']['ProductionYear']
            imdb_rating = data_content['Parent']['ImdbRate']
            seasons = len(data_content['Parent']['ChildContents']['Items'])
            img_url = data_content['Parent']['BackgroundUrl']

        print ('{}/{}: {} --- {} --- {}'.format(str(cnt), str(total_cnt), title, str(content_type), str(imdb_rating)))
        c.execute("INSERT INTO hbogo_content VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);", (id, title, original_title, year, content_type, seasons, imdb_rating, url, img_url, availability_from, availability_to, is_upcoming, 0))
        conn.commit()
        cnt += 1

    conn.close()
