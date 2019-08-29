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

	#
	# Remove any trailing slashes
	#
	if retval["prefix"][len(retval["prefix"]) - 1] == "/":
		retval["prefix"] = retval["prefix"][:-1]

	return(retval)


#
# Split the source file into any prefix after the main prefix and the filename
#
# That is, if the prefix is "foo" and the full path to the file is "foo/bar/baz",
# we'll get "bar" as the prefix and "baz" as the filename.
#
def getSourceFilenamePartsFromPrefix(prefix, file):

	retval = ()

	results = re.search("^" + prefix + "(.*/)?(.*)", file)

	prefix2 = results.group(1)
	file = results.group(2)

	#
	# Remove any leading and trailing slashes
	#
	if prefix2[0] == "/":
		prefix2 = prefix2[1:]

	#
	# Remove any trailing slashes
	#
	if prefix2:
		if prefix2[len(prefix2) - 1] == "/":
			prefix2 = prefix2[:-1]

	return(prefix2, file)


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
	
	rollup_files = {}

	for obj in bucket.objects.filter(Prefix = source_parts["prefix"]):
		(prefix2, file) = getSourceFilenamePartsFromPrefix(source_parts["prefix"], obj.key)
		buckets = getTimeBuckets(file)

		if s3_level == "10min":
			rollup_file = "{}-{}-{}-{}-{}0".format(buckets["year"], buckets["month"], buckets["day"], buckets["hour"], buckets["10min"])

		elif s3_level == "hour":
			rollup_file = "{}-{}-{}-{}".format(buckets["year"], buckets["month"], buckets["day"], buckets["hour"])

		elif s3_level == "day":
			rollup_file = "{}-{}-{}".format(buckets["year"], buckets["month"], buckets["day"])

		elif s3_level == "month":
			rollup_file = "{}-{}".format(buckets["year"], buckets["month"])

		if prefix2:
			rollup_file = "{}/{}/{}".format(
				dest_parts["prefix"], prefix2, rollup_file)
		else:
			rollup_file = "{}/{}".format(
				dest_parts["prefix"], rollup_file)

		if not rollup_file in rollup_files:
			rollup_files[rollup_file] = []
		rollup_files[rollup_file].append(obj.key)
		

	print(json.dumps(rollup_files, indent = 4, sort_keys = True))


