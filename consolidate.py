# :set tabstop=4 softtabstop=4 noexpandtab

import json
import logging.config
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
# Our main entry point.
#
def go(event, context):

	logging.info("TEST INFO")
	s3_source = os.environ["source"]
	s3_dest = os.environ["dest"]

	logger.info("Source S3 bucket: {}".format(s3_source))
	logger.info("Dest S3 bucket: {}".format(s3_dest))

	client = boto3.client("s3")

	results = client.get_paginator('list_objects')
	files = results.paginate(Bucket = s3_source)
	for file in files:
		for obj in file['Contents']:
			print("s3://%s/%s" % (s3_source, obj["Key"]))



