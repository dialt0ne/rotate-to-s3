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
import logging
import os
import re
import signal
import sys
import time

defaultConfigFile = "rotate-to-s3.json"


def getInstanceId():
    h = httplib2.Http()
    # get the instance id from the aws meta data
    url = "http://169.254.169.254/latest/meta-data/instance-id"
    resp, content = h.request(url, "GET")
    # strip out the leading 'i-'
    match = re.search('i-(.+)', content)
    iid = match.group(1)
    return iid


def getConf(filename):
    with open(filename, 'r') as f:
        config = f.read()
        c = json.loads(config)
    return c


def getPid(pidfile):
    with open(pidfile, 'r') as p:
        # remove all trailing whitespace, especially the newline
        pid = p.readline().rstrip()
    return int(pid)


def compressFile(src, dest):
    with open(src, 'rb') as f_src:
        with gzip.open(dest, 'wb') as f_dest:
            f_dest.writelines(f_src)


def testS3(access, secret, bucket, iid, now):
    c = boto.connect_s3(access, secret)
    b = c.create_bucket(bucket)
    k = boto.s3.key.Key(b)
    # only a test key
    test_key = iid + "-" + now + "-test"
    k.key = test_key
    # with test data
    k.set_contents_from_string('Testing S3 at ' + now)
    k.delete()


def uploadtoS3(access, secret, bucket, sourcefile, destinationfile):
    c = boto.connect_s3(access, secret)
    b = c.create_bucket(bucket)
    k = boto.s3.key.Key(b)
    k.key = destinationfile
    k.set_contents_from_filename(sourcefile)


if __name__ == '__main__':
    logging.basicConfig(format="rotate-to-s3.py: %(message)s")
    now = time.strftime('%Y%m%d-%H%M%S')
    parser = argparse.ArgumentParser(prog='rotate-to-s3.py')
    parser.add_argument("-c", "--config", dest="config",
                        default=defaultConfigFile,
                        help="json config file, default: " + defaultConfigFile)
    args = parser.parse_args()
    try:
        conf = getConf(args.config)
    except IOError as (errno, strerror):
        logging.error("Error opening config file %s: %s, quitting",
                      args.config, strerror)
        sys.exit(1)
    try:
        pid = getPid(conf[u'pidfile'])
    except IOError as (errno, strerror):
        logging.error("Error opening pid file %s: %s, quitting",
                      conf[u'pidfile'], strerror)
        sys.exit(1)
    try:
        instanceId = getInstanceId()
    except:
        logging.error("Error getting EC2 instance id, quitting")
        sys.exit(1)
    # try connecting to S3 before we even start
    bucket = conf[u'destination']
    aws_access_key = conf[u'access']
    aws_secret_access_key = conf[u'secret']
    try:
        testS3(aws_access_key, aws_secret_access_key,
               bucket, instanceId, now)
    except boto.exception.NoAuthHandlerFound:
        logging.error("S3 authentication error, quitting")
        sys.exit(2)
    except boto.exception.S3CreateError as (status, reason):
        logging.error("S3 Error creating %s:%s: %s, quitting",
                      bucket, now + 'test', reason)
        sys.exit(2)
    except boto.exception.S3PermissionsError as (reason):
        logging.error("S3 Error with permissions on %s:%s: %s, quitting",
                      bucket, iid + "-" + now + "-test", reason)
        sys.exit(2)
    except:
        logging.error("S3 unknown error, quitting")
        sys.exit(2)
    # rename files prior to rotate
    for src in conf[u'source']:
        logdir = src[u'directory']
        for filename in src[u'files']:
            oldName = logdir + "/" + filename
            oldSize = 0
            if os.path.isfile(oldName) == True:
                oldSize = os.stat(oldName).st_size
			# don't bother with zero-length logfiles
            if oldSize == 0:
                break
            newName = logdir + "/" + now + '-' + filename
            # rotate the logs
            try:
                os.rename(oldName, newName)
            except OSError as (errno, strerror):
                logging.error("Error renaming %s to %s: %s",
                              oldName, newName, strerror)
    # force process to logswitch
    os.kill(pid, signal.SIGUSR1)
    # wait for it to complete
    time.sleep(1)
    # compress logs
    for src in conf[u'source']:
        logdir = src[u'directory']
        for filename in src[u'files']:
            newName = logdir + "/" + now + '-' + filename
            if os.path.isfile(newName) == False:
                break
            zipName = logdir + "/" + now + '-' + filename + '.gz'
            # gzip the file
            try:
                compressFile(newName, zipName)
                os.remove(newName)
            except IOError as (errno, strerror):
                logging.error("Error zipping %s to %s: %s",
                              newName, zipName, strerror)
            except OSError as (errno, strerror):
                logging.error("Error removing after zip %s: %s",
                              newName, strerror)
    # upload logs
    for src in conf[u'source']:
        logdir = src[u'directory']
        for filename in src[u'files']:
            zipName = logdir + "/" + now + '-' + filename + '.gz'
            if os.path.isfile(zipName) == False:
                break
            s3Name = instanceId + '-' + now + '-' + filename + '.gz'
            # push to s3
            try:
                uploadtoS3(aws_access_key, aws_secret_access_key,
                           bucket, zipName, s3Name)
                os.remove(zipName)
            except IOError as (errno, strerror):
                logging.error("Error uploading %s to %s:%s: %s",
                              zipName, bucket, s3Name, strerror)
            except OSError as (errno, strerror):
                logging.error("Error removing after upload %s: %s",
                              zipName, strerror)
            except boto.exception.S3CreateError as (status, reason):
                logging.error("S3 Error creating %s:%s: %s",
                              bucket, s3Name, reason)
            except boto.exception.S3PermissionsError as (reason):
                loggin.error("S3 Error with permissions on %s:%s: %s",
                             bucket, s3Name, reason)
