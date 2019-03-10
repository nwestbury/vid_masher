# YouTube Masher

## Setup

### Requirements
* Python 3.x

### Install Dependencies
```
pip3 install -r requirement.txt
```

Install `ffmpeg` (if on Debian-based OS, `sudo apt install ffmpeg`)

### Google API Setup
Follow the instructions here to get Google's API setup: https://developers.google.com/youtube/v3/quickstart/python

export the DEV_KEY as such `export DEV_KEY='API KEY GOES HERE'`.

### Database Setup

Manually create a PSQL database called "masher" and add `PSQL_USER` and `PSQL_PASS` to the
`secrets.sh` similar to above.

```
$ sudo su postgres
$ createuser --interactive root 
$ CREATE DATABASE masher OWNER root;
$ GRANT ALL ON DATABASE masher TO root; 
```

## Run

Construction pipeline has 3 steps: download, split, and populate DB

Download 
```
python3 downloader.py [l/d] [channel_id]
python3 downloader.py list UCYxRlFDqcWM4y7FfpiAN3KQ
python3 downloader.py download UCYxRlFDqcWM4y7FfpiAN3KQ
```