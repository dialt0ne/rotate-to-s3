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
import sys
import time

configfile = "rotate-to-s3.json"

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

def testS3(access,secret,now):
  # connect to s3
  c = boto.connect_s3(access,secret)
  # create/open bucket
  b = c.create_bucket(bucket)
  # set the key
  k = boto.s3.key.Key(b)
  k.key = now+'-test'
  # upload the file
  k.set_contents_from_string('Testing S3 at '+now)
  k.delete()

def uploadtoS3(access,secret,sourcefile,bucket,destinationfile):
  # connect to s3
  c = boto.connect_s3(access,secret)
  # create/open bucket
  b = c.create_bucket(bucket)
  # set the key
  k = boto.s3.key.Key(b)
  k.key = destinationfile
  # upload the file
  k.set_contents_from_filename(sourcefile)

if __name__ == '__main__':
	try:
		with open(configfile,'r') as f:
			config = f.read()
	except IOError as (errno, strerror):
		print "Error opening config file {0}: {1}".format(configfile, strerror)
		sys.exit(1)
	conf = json.loads(config)
	# prep for rotate
	now = time.strftime('%Y%m%d-%H%M%S')
	pid = getpid(conf[u'pidfile'])
	bucket = conf[u'destination']
	aws_access_key = conf[u'access']
	aws_secret_access_key = conf[u'secret']
	instanceid = getinstanceid();
	try:
		testS3(aws_access_key,aws_secret_access_key,now)
	except boto.exception.NoAuthHandlerFound:
		print "S3 authentication error, quitting"
		sys.exit(2)
	except boto.exception.S3CreateError as (status, reason):
		print "S3 Error creating {0}:{1}: {2}".format(bucket, now+'test', reason)
		sys.exit(2)
	except boto.exception.S3PermissionsError as (reason):
		print "S3 Error with permissions on {0}:{1}: {2}".format(bucket, now+'test', reason)
		sys.exit(2)
	except:
		print "S3 unknown error, quitting"
		sys.exit(2)
	# rename files prior to rotate
	for src in conf[u'source']:
		logdir = src[u'directory']
		for filename in src[u'files']:
			oldname = logdir +"/"+    filename
			oldsize = 0
			if os.path.isfile(oldname) == True:
				oldsize = os.stat(oldname).st_size
			if oldsize == 0:
				break
			newname = logdir +"/"+    now +'-'+ filename
			# rotate the logs
			try:
				os.rename(oldname,newname)
			except OSError as (errno, strerror):
				print "Error renaming {0} to {1}: {2}".format(oldname, newname, strerror)
	# force nginx to logswitch
	os.kill(pid,signal.SIGUSR1)
	# wait for it to complete
	time.sleep(1)
	# compress logs
	for src in conf[u'source']:
		logdir = src[u'directory']
		for filename in src[u'files']:
			newname = logdir +"/"+    now +'-'+ filename
			if os.path.isfile(newname) == False:
				break
			zipname = logdir +"/"+    now +'-'+ filename +'.gz'
			# gzip the file
			try:
				compressfile(newname,zipname)
				os.remove(newname)
			except IOError as (errno, strerror):
				print "Error zipping {0} to {1}: {2}".format(newname, zipname, strerror)
			except OSError as (errno, strerror):
				print "Error removing after zip {0}: {1}".format(newname, strerror)
	# upload logs
	for src in conf[u'source']:
		logdir = src[u'directory']
		for filename in src[u'files']:
			zipname = logdir +"/"+    now +'-'+ filename +'.gz'
			if os.path.isfile(zipname) == False:
				break
			s3name = instanceid +'-'+ now +'-'+ filename +'.gz'
			# push to s3
			try:
				uploadtoS3(aws_access_key,aws_secret_access_key,zipname,bucket,s3name)
				os.remove(zipname)
			except IOError as (errno, strerror):
				print "Error uploading {0} to {1}:{2}: {3}".format(zipname, bucket, s3name, strerror)
			except OSError as (errno, strerror):
				print "Error removing after upload {0}: {1}".format(zipname, strerror)
			except boto.exception.S3CreateError as (status, reason):
				print "S3 Error creating {0}:{1}: {2}".format(bucket, s3name, reason)
			except boto.exception.S3PermissionsError as (reason):
				print "S3 Error with permissions on {0}:{1}: {2}".format(bucket, s3name, reason)
			

