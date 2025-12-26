# GitHub Actions Database Persistence

## How It Works

Each GitHub Actions run starts with a **fresh virtual machine**, which means the database is recreated from scratch each time. To fix this, we use **GitHub Actions Cache** to persist the database between runs.

### The Problem (Before Fix)

1. **First run**: Creates new `jobs.db` → All jobs are "new" → Emails all jobs
2. **Second run**: Creates new `jobs.db` again → All jobs are "new" again → Emails all jobs again
3. **Result**: You get duplicate emails for the same jobs every day

### The Solution (After Fix)

1. **First run**: 
   - No cached database exists → Creates new `jobs.db`
   - Scrapes jobs → Adds to database
   - Saves database to cache
   - Emails new jobs

2. **Second run**:
   - **Restores database from cache** → Uses existing `jobs.db` with previous jobs
   - Scrapes jobs → Only adds jobs that don't exist yet
   - Updates database in cache
   - Emails only the NEW jobs (not duplicates)

## What Changed

The workflow now:
1. **Restores** the database from cache at the start (if it exists)
2. **Runs** the scraper (which uses the existing database)
3. **Saves** the updated database to cache for the next run

## Cache Details

- **Cache key**: `jobs-database-<OS>`
- **Cache location**: GitHub Actions cache (managed automatically)
- **Cache retention**: GitHub keeps caches for 7 days if not accessed
- **Cache size limit**: 10 GB per repository (plenty for a SQLite database)

## First Run Behavior

On the **very first run**:
- No cached database exists yet
- All jobs will be emailed (this is expected!)
- Database is saved to cache for future runs

On **subsequent runs**:
- Database is restored from cache
- Only truly new jobs are added
- Only new jobs are emailed

## Manual Testing

To test that it's working:

1. **First test run**: Should email all jobs (expected)
2. **Second test run** (trigger immediately): Should email only new jobs or nothing
3. **Check logs**: Look for "Skipped X duplicate job(s)" in the output

## Troubleshooting

### Still getting duplicate emails?

1. Check the workflow logs - look for "Skipped X duplicate job(s)"
2. If you see "Added X new jobs" for jobs you've seen before, the cache might not be working
3. Try manually clearing the cache:
   - Go to Settings → Actions → Caches
   - Delete the `jobs-database-*` cache
   - Next run will start fresh

### Database not persisting?

- Check workflow logs for cache restore/save steps
- Verify the cache step completed successfully
- Cache might have expired (7 days of inactivity)

## Alternative: Download Database Manually

If you want to keep a local copy of your database:

1. Go to **Actions** tab
2. Click on a completed workflow run
3. Scroll down to **Artifacts**
4. Download `jobs-database` artifact
5. Extract `jobs.db` file

This is useful for:
- Backing up your database
- Viewing jobs locally with `utils/view_database.py`
- Starting fresh (delete the artifact, next run creates new DB)

