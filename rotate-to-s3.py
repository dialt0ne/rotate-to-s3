#!/usr/bin/python
#
# rotate-to-s3.py
#
# ATonns Wed Mar 14 19:40:57 UTC 2012
import boto
import gzip
import httplib2
import os
import re
import signal
import time

logdir = "/var/www/logs"
filename = "healthguru.access.log"
pidfile = "/var/run/nginx.pid"
destination_bucket = "live-test-logs"

def getinstanceid():
  h = httplib2.Http()
  # get the instance id from the aws meta data
  resp, content = h.request("http://169.254.169.254/latest/meta-data/instance-id", "GET")
  # strip out the leading 'i-'
  match = re.search('i-(.+)',content)
  id = match.group(1)
  return id

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

def uploadtos3(sourcefile,destinationfile):
  # connect to s3
  #c = boto.connect_s3(AWS_ACCESS_KEY_ID,AWS_SECRET_ACCESS_KEY)
  c = boto.connect_s3()
  # create/open bucket
  b = c.create_bucket(destination_bucket)
  # set the key
  from boto.s3.key import Key
  k = Key(b)
  k.key = destinationfile
  # upload the file
  k.set_contents_from_filename(sourcefile)

if __name__ == '__main__':
	# prep for rotate
	pid = getpid(pidfile)
	now = time.strftime('%Y%m%d-%H%M%S')
	oldname = logdir +"/"+                   filename
	newname = logdir +"/"+         now +'-'+ filename
	zipname = logdir +"/"+         now +'-'+ filename +'.gz'
	s3name = getinstanceid() +'-'+ now +'-'+ filename +'.gz'
	# rotate the logs
	os.rename(oldname,newname)
	# force nginx to logswitch
	os.kill(pid,signal.SIGUSR1)
	# wait for it to complete
	time.sleep(1)
	# gzip the file
	compressfile(newname,zipname)
	os.remove(newname)
	# push to s3
	uploadtos3(zipname,s3name)

