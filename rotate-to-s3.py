#!/usr/bin/python
#
# rotate-to-s3.py
#
# ATonns Wed Mar 14 19:40:57 UTC 2012
import boto
import gzip
import httplib2
import json
import os
import re
import signal
import time

config = """
{
    "destination": "live-test-logs",
    "source": [
        {
            "directory": "/var/www/logs",
            "files": [
                "healthguru.access.log",
                "healthguru.stage.access.log"
            ]
        }
    ],
    "pidfile": "/var/run/nginx.pid"
}
"""

def getinstanceid():
  h = httplib2.Http()
  # get the instance id from the aws meta data
  resp, content = h.request("http://169.254.169.254/latest/meta-data/instance-id", "GET")
  # strip out the leading 'i-'
  match = re.search('i-(.+)',content)
  instanceid = match.group(1)
  return instanceid

def getpid(pidfile):
  p = open(pidfile,"r")
  # remove all trailing whitespace, especially the newline
  pid = p.readline().rstrip()
  return int(pid)

def compressfile(sourcefile,destinationfile):
  # source
  f_in = open(sourcefile, 'rb')
  # destination
  f_out = gzip.open(destinationfile, 'wb')
  # go
  f_out.writelines(f_in)
  f_out.close()
  f_in.close()

def uploadtos3(sourcefile,bucket,destinationfile):
  # connect to s3
  #c = boto.connect_s3(AWS_ACCESS_KEY_ID,AWS_SECRET_ACCESS_KEY)
  c = boto.connect_s3()
  # create/open bucket
  b = c.create_bucket(bucket)
  # set the key
  from boto.s3.key import Key
  k = Key(b)
  k.key = destinationfile
  # upload the file
  k.set_contents_from_filename(sourcefile)

def _decode_list(data):
    rv = []
    for item in data:
        if isinstance(item, unicode):
            item = item.encode('utf-8')
        elif isinstance(item, list):
            item = _decode_list(item)
        elif isinstance(item, dict):
            item = _decode_dict(item)
        rv.append(item)
    return rv

def _decode_dict(data):
    rv = {}
    for key, value in data.iteritems():
        if isinstance(key, unicode):
           key = key.encode('utf-8')
        if isinstance(value, unicode):
           value = value.encode('utf-8')
        elif isinstance(value, list):
           value = _decode_list(value)
        elif isinstance(value, dict):
           value = _decode_dict(value)
        rv[key] = value
    return rv

if __name__ == '__main__':
	conf = json.loads(config, object_hook=_decode_dict)
	# prep for rotate
	now = time.strftime('%Y%m%d-%H%M%S')
	pid = getpid(conf['pidfile'])
	bucket = conf['destination']
	for src in conf['source']:
		logdir = src['directory']
		for filename in src['files']:
			oldname = logdir +"/"+                   filename
			newname = logdir +"/"+         now +'-'+ filename
			# rotate the logs
			os.rename(oldname,newname)
	# force nginx to logswitch
	os.kill(pid,signal.SIGUSR1)
	# wait for it to complete
	time.sleep(1)
	for src in conf['source']:
		logdir = src['directory']
		for filename in src['files']:
			newname = logdir +"/"+         now +'-'+ filename
			zipname = logdir +"/"+         now +'-'+ filename +'.gz'
			s3name = getinstanceid() +'-'+ now +'-'+ filename +'.gz'
			# gzip the file
			compressfile(newname,zipname)
			os.remove(newname)
			# push to s3
			uploadtos3(zipname,bucket,s3name)

