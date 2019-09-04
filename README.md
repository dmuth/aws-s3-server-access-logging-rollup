

## Setup and Deployment

- Copy `serverless.yml.example` to `serverless.yml`
- Edit `serverless.yml` to include your source and destination buckets and paths
- Deploy the app with `sls deploy`

Once deployed, the default is that the script will run every 10 minutes.
In certain circumstances (such as if you have over 10,000 files), the script
may not complete in 10 minutes.  In that case, either increasing the rate to 
`1 hour` and/or decreasing the level to `hour` or even `10min`  is recommended 
until the backlog of logs to be rolled up is cleared out.

Alternatively, instead of immediately deploying, serverless could be run in local
mode as described below, so that progress can be observed directly, and more time
be given for initial rollups to take place.


### Deployment recommendations

Enable the debug flags `keep` and `dryrun` and then test locally.


## Testing and debugging

### Run locally with all debug functions set

  - `serverless invoke local -f rollup -d keep:dryrun:overwrite`
  - Debug flags:
     - `keep` - Keep the source files
     - `dryrun` - Do not write destination rollups or remove source logs
     - `overwrite` - Overwrite the destination rollups if they exist
        - Default behavior is to read in the contents of the rollups and append to them, as rollups may be done multiple times within a rollup time period.
  - (note that dryrun and overwrite together don't make much sense)


### Run in the foreground with logging enabled to see the output:

- `serverless invoke -f rollup -l`


### Get the logging destinations for all current buckets

This can be pasted in on the command line to get a list of all S3
buckets that your current AWS credentials have access to, and
where they send their logs:

```
for BUCKET in $(aws s3 ls | awk '{print $3}' )
do 
	echo -n "$BUCKET: "
	aws s3api get-bucket-logging --bucket $BUCKET \
		| jq -r '.LoggingEnabled | "s3://" + "\(.TargetBucket)" + "/" + "\(.TargetPrefix)" ' \
		| tr -d '\n'
	echo
done
```


## Troubleshooting

Aka "if things go wrong".

Because we're making connections to S3, which is a web service, things
might go a little wrong.  If at any point there is an error reading or
writing an object, the entire script will stop.  This is by design.
The consequences of the error depend on where in the script it stops.

If the script stops:

- While reading source files
   - Nothing will be changed
- While writing the destination file
   - If the write to the destination file succeeds, it will overwrite what's there, if not, the original destination file will be untouched and the script will throw an exception, so nothing will be changed.
- While removing the source files
   - If this happens, 1 or more source files may be re-rolled up on the next execution.  This will result in duplicate events in the rollups.  This however could be filtered out based the unique value that appears to be in each log entry.


Care was taken when building this app to minimize the chance of data loss
and instead err on the side of having duplicate data, which may be filtered out.



