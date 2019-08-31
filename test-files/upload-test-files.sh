#!/bin/bash
#
# This script will upload multiple copies of the test files
# to an S3 location for testing purposes.
#


# Errors are fatal
set -e


if test ! "$1"
then
	echo "! "
	echo "! Syntax: $0 s3://bucket/dir/"
	echo "! "
	echo "! Test files"
	echo "! "
	exit 1
fi

#
# Get our destination and remove trailing slashes because
# they'll screw everything up.
#
DEST=$1
DEST=$(echo $DEST | sed 's/\/*$//g')

#
# Change to the directory of this script 
#
pushd $(dirname $0) > /dev/null

echo "# "
echo "# Uploading copies of the test logs to ${DEST}..."
echo "# "

aws s3 sync s3/1 ${DEST}/1
aws s3 sync s3/1 ${DEST}/2
aws s3 sync s3/1 ${DEST}/3

echo "# Done!"

