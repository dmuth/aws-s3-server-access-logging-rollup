

## Setup and Deployment

- Copy `serverless.yml.example` to `serverless.yml`
- Edit `serverless.yml` to include your source and destination buckets and paths
- Deploy the app with `sls deploy`


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


## Troubleshooting

Aka "if things go wrong".

Because we're making connections to S3, which is a web service, things
might go a little wrong.  If at any point there is an error reading or
writing an object, the entire script will stop.  This is by design.
The consequences of the error depend on where in the script it stops.

If the script stops:

- While reading source files
   - Nothing will be changed
- While writing the destation file
   - If there was previously data in the destination file, this presents a race condition where data may be list.  
      - I need to come up with a way to address--perhaps by never removing the dest file but instead by writing a new dest file.  That's not perfect, but it will work.
- While removing the source files
   - If this happens, 1 or more source files may be re-rolled up on the next execution.  This will result in duplicate events in the rollups.  This however could be filtered out based the unique value that appears to be in each log entry.


