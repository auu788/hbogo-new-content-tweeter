## Overview

Python3 script which can fetch data from polish HBO Go content DB through their API, track changes between their DB and script's DB and post info about changes on Twitter in polish language.

Living example: https://twitter.com/NowosciHBOGo

## Config

There is a `config.ini` file, where you can set:
- `DatabaseFile` name,
- `PostTweets` bool (default: **False**)
- your Twitter API credentials ( https://apps.twitter.com/ )

## Required modules

```
sqlite3
Twython
```

## First time usage

Open a command prompt from within a project folder, and run `python3 main.py --init`.

### Options
- `-i`, `--init`
  - Creates entirely new DB
- `-t`, `--tweet`
  - Posts about changes on Twitter (you can set it in `config.ini` also)
