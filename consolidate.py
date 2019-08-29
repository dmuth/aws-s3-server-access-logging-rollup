# :set tabstop=4 softtabstop=4 noexpandtab

import json
import logging.config
import re
import sys
import os

import boto3


#
# The Python logger in AWS Lambda has a preset format.
# So we'll need to remove all handlers and add a new handler
# with the format we want and write to stdout.
#
logger = logging.getLogger()
for handler in logger.handlers:
	logger.removeHandler(handler)
handler = logging.StreamHandler(sys.stdout)

format = '%(asctime)s:%(levelname)s: %(message)s'
handler.setFormatter(logging.Formatter(format))
logger.addHandler(handler)
logger.setLevel(logging.INFO)



#
# Grab the bucket name and prefix from our bucket
# The "s3://" part is optional and can be dropped.
#
def getBucketParts(bucket):
	retval = {}

	results = re.search("^(s3://)?([^/]+)(/)?(.*)?", bucket)

	retval["bucket"] = results.group(2)
	retval["prefix"] = results.group(4)
	if not retval["prefix"]:
		retval["prefix"] = ""

	return(retval)


#
# Remove the leading prefix from the source filename
#
def getSourceFilenameFromPrefix(prefix, file):

	retval = ""

	results = re.search("^" + prefix + "(.*)", file)

	#
	# Remove any leading slashes.
	#
	retval = results.group(1)
	if retval[0] == "/":
		retval = retval[1:]

	return(retval)


#
# Extract the various time values from a file
#
def getTimeBuckets(file):

	retval = {}

	results = re.search("([0-9]{4})-([0-9]{2})-([0-9]{2})-([0-9]{2})-([0-9])", file)
	retval["year"] = results.group(1)
	retval["month"] = results.group(2)
	retval["day"] = results.group(3)
	retval["hour"] = results.group(4)
	retval["10min"] = results.group(5)

	return(retval)


#
# Our main entry point.
#
def go(event, context):

	#
	# Grab our arguments
	#
	s3_source = os.environ["source"]
	s3_dest = os.environ["dest"]
	s3_level = os.getenv("level", "10min")
	logger.info("Source S3 bucket: {}".format(s3_source))
	logger.info("Dest S3 bucket: {}".format(s3_dest))
	logger.info("Consolidation level: {}".format(s3_level))

	if s3_level not in ["10min", "hour", "day", "month"]:
		raise Exception("Unknown S3 consolidation level: {}".format(s3_level))

	#
	# Parse our buckets into name and prefix
	#
	source_parts = getBucketParts(s3_source)
	dest_parts = getBucketParts(s3_dest)
	logger.info("Source parts: {}".format(source_parts))
	logger.info("Dest parts: {}".format(dest_parts))

	s3 = boto3.resource('s3')
	bucket = s3.Bucket(source_parts["bucket"])
	
	for obj in bucket.objects.filter(Prefix = source_parts["prefix"]):
		file = getSourceFilenameFromPrefix(source_parts["prefix"], obj.key)
		buckets = getTimeBuckets(file)
		print(obj.key, buckets)


