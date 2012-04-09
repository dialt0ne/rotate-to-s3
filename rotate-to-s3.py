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

if __name__ == '__main__':
	conf = json.loads(config)
	# prep for rotate
	now = time.strftime('%Y%m%d-%H%M%S')
	pid = getpid(conf[u'pidfile'])
	bucket = conf[u'destination']
	# rename files prior to rotate
	for src in conf[u'source']:
		logdir = src[u'directory']
		for filename in src[u'files']:
			oldname = logdir +"/"+                   filename
			newname = logdir +"/"+         now +'-'+ filename
			# rotate the logs
			try:
				os.rename(oldname,newname)
			except OSError as (errno, strerror):
				print "Error moving {0} to {1}: {2}".format(oldname, newname, strerror)
	# force nginx to logswitch
	os.kill(pid,signal.SIGUSR1)
	# wait for it to complete
	time.sleep(1)
	# compress logs
	for src in conf[u'source']:
		logdir = src[u'directory']
		for filename in src[u'files']:
			newname = logdir +"/"+         now +'-'+ filename
			zipname = logdir +"/"+         now +'-'+ filename +'.gz'
			# gzip the file
			try:
				compressfile(newname,zipname)
				os.remove(newname)
			except IOError as (errno, strerror):
				print "Error zipping {0} to {1}: {2}".format(newname, zipname, strerror)
	# upload logs
	for src in conf[u'source']:
		logdir = src[u'directory']
		for filename in src[u'files']:
			zipname = logdir +"/"+         now +'-'+ filename +'.gz'
			s3name = getinstanceid() +'-'+ now +'-'+ filename +'.gz'
			# push to s3
			try:
				uploadtos3(zipname,bucket,s3name)
			except IOError as (errno, strerror):
				print "Error uploading {0} to {1}:{2}: {3}".format(zipname, bucket, s3name, strerror)

