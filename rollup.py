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
# Extract the bucket and object from a full S3 path
#
def parseS3Path(source):

	retval = {}

	results = re.search("^(s3://)?([^/]+)/(.*)", source)

	retval["bucket"] = results.group(2)
	retval["key"] = results.group(3)

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
# Turn our list of files into an array of what files get rolled up into what.
#
def getRollupFiles(s3_level, s3_source, source, dest):

	retval = {}

	source_bucket = source["bucket"]
	source_prefix = source["prefix"]
	dest_bucket = dest["bucket"]
	dest_prefix = dest["prefix"]

	for obj in s3_source.objects.filter(Prefix = source_prefix):

		(prefix2, file) = getSourceFilenamePartsFromPrefix(source_prefix, obj.key)
		buckets = getTimeBuckets(file)

		if s3_level == "10min":
			rollup_file = "{}-{}-{}-{}-{}0".format(
				buckets["year"], buckets["month"], 
				buckets["day"], buckets["hour"], buckets["10min"])

		elif s3_level == "hour":
			rollup_file = "{}-{}-{}-{}".format(
				buckets["year"], buckets["month"], 
				buckets["day"], buckets["hour"])

		elif s3_level == "day":
			rollup_file = "{}-{}-{}".format(
				buckets["year"], buckets["month"], 
				buckets["day"])

		elif s3_level == "month":
			rollup_file = "{}-{}".format(buckets["year"], buckets["month"])

		if prefix2:
			rollup_file = "{}/{}/{}".format(
				dest_prefix, prefix2, rollup_file)

		else:
			rollup_file = "{}/{}".format(
				dest_prefix, rollup_file)

		rollup_file = "{}/{}".format(dest_bucket, rollup_file)

		if not rollup_file in retval:
			retval[rollup_file] = []
		retval[rollup_file].append("{}/{}".format(source_bucket, obj.key))

	return(retval)		


#
# Read an S3 object and return the data
#
def readS3Object(s3, source):

	parts = parseS3Path(source)
	obj = s3.Object(bucket_name = parts["bucket"], key = parts["key"])
	response = obj.get()
	retval = response['Body'].read()

	return(retval)


#
# Delete an S3 object
#
def deleteS3Object(s3, source):
	parts = parseS3Path(source)
	obj = s3.Object(bucket_name = parts["bucket"], key = parts["key"])
	obj.delete()


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
	debug = {
		"keep": os.getenv("debug_keep", False),
		"dryrun": os.getenv("debug_dryrun", False),
		"overwrite": os.getenv("debug_overwrite", False),
		}

	#
	# Grab debug flags if present.
	#
	if type(event) is str:
		fields = event.split(":")
		logger.info("-d flags provided: {}".format(fields))

		if "keep" in fields:
			debug["keep"] = True
		if "dryrun" in fields:
			debug["dryrun"] = True
		if "overwrite" in fields:
			debug["overwrite"] = True


	if s3_level not in ["10min", "hour", "day", "month"]:
		raise Exception("Unknown S3 consolidation level: {}".format(s3_level))

	logger.info("Source S3 bucket: {}".format(s3_source))
	logger.info("Dest S3 bucket: {}".format(s3_dest))
	logger.info("Consolidation level: {}".format(s3_level))
	logger.info("Debug flags: {}".format(debug))

	#
	# Parse our buckets into name and prefix
	#
	source_parts = getBucketParts(s3_source)
	dest_parts = getBucketParts(s3_dest)
	logger.info("Source parts: {}".format(source_parts))
	logger.info("Dest parts: {}".format(dest_parts))

	s3 = boto3.resource("s3")
	s3_source = s3.Bucket(source_parts["bucket"])
	s3_dest = s3.Bucket(dest_parts["bucket"])
	
	rollup_files = getRollupFiles(s3_level, s3_source, source_parts, dest_parts)

	for dest in rollup_files:

		data = b""

		#
		# If the output file already exists, read it in.
		# This is because multiple runs could catch new inputs
		# that weren't present before.
		#
		if not debug["overwrite"]:
			try: 
				data = readS3Object(s3, dest)
				logger.info("Read {} bytes from pre-existing {}".format(
					len(data), dest))

			except Exception as e:
				if e.operation_name != "GetObject":
					raise(e)
				logger.info(
					"The dest {} appears not to exist, but that's fine, continuing!".format(
					dest))

		else:
			#
			# Overwrite mode is enabled, so remove the destination object.
			#
			logger.info("Debug: overwrite: Remove the dest S3 object {}".format(dest))
			deleteS3Object(s3, dest)


		#
		# Read our input files and write them to the output
		#
		for source in rollup_files[dest]:
			results = readS3Object(s3, source)
			data += results
			logger.info("Read {} bytes from {}, now have {} bytes".format(
				len(results), source, len(data)))

		logger.info("Writing {} bytes to rollup {}...".format(
			len(data), dest))

		if not debug["dryrun"]:
			parts = parseS3Path(dest)
			obj = s3.Object(bucket_name = parts["bucket"], key = parts["key"])
			obj.put(Body = data)

		else:
			logger.info("Debug: dryrun: Don't write dest S3 object {}".format(dest))

		#
		# Now delete our input files
		#
		for source in rollup_files[dest]:
			if not debug["keep"]:
				logger.info("Removing source file {}...".format(source))
				deleteS3Object(s3, source)

			else: 
				logger.info("Debug: keep: Don't remove source S3 object {}".format(source))

	logger.info("Done!")	

