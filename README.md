
# AWS S3 Server Access Logging Rollup

AWS S3 logging is great for keeping track of accesses to your S3 buckets, but
it is *notorious* for just spamming your target bucket with many small files
many times per minute:

```
2019-09-14 13:26:38        835 s3/www.pa-furry.org/2019-09-14-17-26-37-5B75705EA0D67AF7
2019-09-14 13:26:46        333 s3/www.pa-furry.org/2019-09-14-17-26-45-C8553CA61B663D7A
2019-09-14 13:26:55        333 s3/www.pa-furry.org/2019-09-14-17-26-54-F613777CE621F257
2019-09-14 13:26:56        333 s3/www.pa-furry.org/2019-09-14-17-26-55-99D355F57F3FABA9
2019-09-14 13:27:06       1013 s3/www.pa-furry.org/2019-09-14-17-27-05-35FDE41D8D27DE13
2019-09-14 13:27:06        333 s3/www.pa-furry.org/2019-09-14-17-27-05-ECC1ECDB7FA3D2E3
2019-09-14 13:27:21        333 s3/www.pa-furry.org/2019-09-14-17-27-20-995D36CE306B33BD
2019-09-14 13:27:28       1386 s3/www.pa-furry.org/2019-09-14-17-27-27-18AE0DD17C532746
2019-09-14 13:27:31        333 s3/www.pa-furry.org/2019-09-14-17-27-30-DDF41B2D86C1DD77
```

This app instead lets you perform rollup on monthly, daily, hourly, or 10 minute
intervals so that you have far fewer files:

```
2019-09-10 20:02:56    3930277 rollup-day/www.pa-furry.org/2019-09-10
2019-09-11 20:02:56    4304119 rollup-day/www.pa-furry.org/2019-09-11
2019-09-12 20:02:56    3991237 rollup-day/www.pa-furry.org/2019-09-12
```

The is written in Python, and deployed as a Lambda function that will run every
10 minutes by default.  Deployment is done with <a href="https://serverless.com/">Serverless</a>.


## Setup and Deployment

- Copy `serverless.yml.example` to `serverless.yml`
- Edit `serverless.yml` to include your source and destination buckets and paths
- Install Serverless: `npm install -g serverless`
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

### Set logging policy for 1 or more buckets

Instructions are at: <a href="https://docs.aws.amazon.com/cli/latest/reference/s3api/put-bucket-logging.html">https://docs.aws.amazon.com/cli/latest/reference/s3api/put-bucket-logging.html</a>

It's only recommend going through that if you have dozens or buckets or more.  Otherwise, the S3 UI is generally sufficient.


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


## Bugs/Contact

Here's how to get in touch with me:

- <a href="http://twitter.com/dmuth">Twitter</a>
- <a href="http://facebook.com/dmuth">Facebook</a>
- <a href="http://www.dmuth.org/">Blog</a>
- <a href="mailto:doug.muth@gmail.com">Email</a>



