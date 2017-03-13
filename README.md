## Overview

Python3 script which can fetch data from polish HBO Go content DB through their API, track changes between their DB and script's DB and post info about changes on Twitter in polish language.

## Config

There is a 'config.ini' file, where you can set 'DatabaseFile' name, 'PostTweets' bool (default: **False**) and your Twitter API credentials ( https://apps.twitter.com/ )

## Required modules

'''
sqlite3
Twython
'''

## Usage

To create new DB, use:
'''
python3 main.py --init
'''

If you have ''PostTweets'' set to **False** in 'config.ini' and want to occasionally run with ability to tweeting messages, use:
'''
python3 main.py --tweet
'''
