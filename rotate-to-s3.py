#!/usr/bin/python
#
# rotate-to-s3.py
#
# ATonns Wed Mar 14 19:40:57 UTC 2012
import argparse
import boto
import gzip
import httplib2
import json
import os
import re
import signal
import sys
import time

defaultConfigFile = "rotate-to-s3.json"

def getInstanceId():
  h = httplib2.Http()
  # get the instance id from the aws meta data
  resp, content = h.request("http://169.254.169.254/latest/meta-data/instance-id", "GET")
  # strip out the leading 'i-'
  match = re.search('i-(.+)',content)
  iid = match.group(1)
  return iid

def getConf(filename):
  with open(filename,'r') as f:
    config = f.read()
    c = json.loads(config)
  return c

def getPid(pidfile):
  with open(pidfile,'r') as p:
    # remove all trailing whitespace, especially the newline
    pid = p.readline().rstrip()
  return int(pid)

def compressFile(sourcefile,destinationfile):
  with open(sourcefile, 'rb') as f_in:
    with gzip.open(destinationfile, 'wb') as f_out:
      f_out.writelines(f_in)

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
  parser = argparse.ArgumentParser(prog='rotate-to-s3.py')
  parser.add_argument("-c","--config",dest="config",default=defaultConfigFile,
    help="config file (json), default: "+defaultConfigFile)
  args = parser.parse_args()
  try:
    conf = getConf(args.config)
  except IOError as (errno, strerror):
    print "Error opening config file {0}: {1}, quitting".format(args.config, strerror)
    sys.exit(1)
  # prep for rotate
  now = time.strftime('%Y%m%d-%H%M%S')
  try:
    pid = getPid(conf[u'pidfile'])
  except IOError as (errno, strerror):
    print "Error opening pid file {0}: {1}, quitting".format(conf[u'pidfile'], strerror)
    sys.exit(1)
  bucket = conf[u'destination']
  aws_access_key = conf[u'access']
  aws_secret_access_key = conf[u'secret']
  try:
    instanceId = getInstanceId()
  except:
    print "Error getting EC2 instance id, quitting"
    sys.exit(1)
  try:
    testS3(aws_access_key,aws_secret_access_key,now)
  except boto.exception.NoAuthHandlerFound:
    print "S3 authentication error, quitting"
    sys.exit(2)
  except boto.exception.S3CreateError as (status, reason):
    print "S3 Error creating {0}:{1}: {2}, quitting".format(bucket, now+'test', reason)
    sys.exit(2)
  except boto.exception.S3PermissionsError as (reason):
    print "S3 Error with permissions on {0}:{1}: {2}, quitting".format(bucket, now+'test', reason)
    sys.exit(2)
  except:
    print "S3 unknown error, quitting"
    sys.exit(2)
  # rename files prior to rotate
  for src in conf[u'source']:
    logdir = src[u'directory']
    for filename in src[u'files']:
      oldName = logdir +"/"+    filename
      oldSize = 0
      if os.path.isfile(oldName) == True:
        oldSize = os.stat(oldName).st_size
      if oldSize == 0:
        break
      newName = logdir +"/"+    now +'-'+ filename
      # rotate the logs
      try:
        os.rename(oldName,newName)
      except OSError as (errno, strerror):
        print "Error renaming {0} to {1}: {2}".format(oldName, newName, strerror)
  # force nginx to logswitch
  os.kill(pid,signal.SIGUSR1)
  # wait for it to complete
  time.sleep(1)
  # compress logs
  for src in conf[u'source']:
    logdir = src[u'directory']
    for filename in src[u'files']:
      newName = logdir +"/"+    now +'-'+ filename
      if os.path.isfile(newName) == False:
        break
      zipName = logdir +"/"+    now +'-'+ filename +'.gz'
      # gzip the file
      try:
        compressFile(newName,zipName)
        os.remove(newName)
      except IOError as (errno, strerror):
        print "Error zipping {0} to {1}: {2}".format(newName, zipName, strerror)
      except OSError as (errno, strerror):
        print "Error removing after zip {0}: {1}".format(newName, strerror)
  # upload logs
  for src in conf[u'source']:
    logdir = src[u'directory']
    for filename in src[u'files']:
      zipName = logdir +"/"+    now +'-'+ filename +'.gz'
      if os.path.isfile(zipName) == False:
        break
      s3Name = instanceId +'-'+ now +'-'+ filename +'.gz'
      # push to s3
      try:
        uploadtoS3(aws_access_key,aws_secret_access_key,zipName,bucket,s3Name)
        os.remove(zipName)
      except IOError as (errno, strerror):
        print "Error uploading {0} to {1}:{2}: {3}".format(zipName, bucket, s3Name, strerror)
      except OSError as (errno, strerror):
        print "Error removing after upload {0}: {1}".format(zipName, strerror)
      except boto.exception.S3CreateError as (status, reason):
        print "S3 Error creating {0}:{1}: {2}".format(bucket, s3Name, reason)
      except boto.exception.S3PermissionsError as (reason):
        print "S3 Error with permissions on {0}:{1}: {2}".format(bucket, s3Name, reason)
      

