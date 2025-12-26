# Daily Email Logic Explanation

## How It Works

When you run `python main.py` daily, here's exactly what happens:

### Step 1: Scraping (scrape_all_boards)
1. **Scrapes job boards** - Gets jobs posted TODAY (if `FILTER_TODAY_ONLY = True`)
2. **Checks database** - For each job found, checks if it already exists in database
3. **Adds only NEW jobs** - Only jobs that don't exist yet are added to database
   - If a job already exists → skipped (won't be added again)
   - If a job is new → added with `created_at = today` and `emailed = 'no'`

### Step 2: Email (send_daily_email)
1. **Gets today's new jobs** - Only jobs that were:
   - Added to database TODAY (`created_at >= today`)
   - Haven't been emailed yet (`emailed = 'no'`)
2. **Sends email** - Emails you all the new jobs found
3. **Marks as emailed** - After successful email, marks jobs as `emailed = 'yes'`

## Key Points

✅ **Only NEW jobs are emailed** - Jobs that were already in the database from previous days are NOT included

✅ **Jobs are only emailed once** - Once a job is emailed, it's marked as `emailed = 'yes'` and won't be sent again

✅ **Only today's scraped jobs** - The email only includes jobs that were scraped and added to the database during today's run

✅ **Duplicate prevention** - If the same job is found again (same `job_id`), it won't be added to database again

## Example Daily Flow

**Day 1 (Monday):**
- Scrapes 5 new jobs → Adds all 5 to database
- Emails you 5 jobs
- Marks all 5 as emailed

**Day 2 (Tuesday):**
- Scrapes 3 new jobs → Adds all 3 to database
- Also finds 2 jobs from Monday (still posted today) → Skips them (already in database)
- Emails you only the 3 NEW jobs from Tuesday
- Marks those 3 as emailed

**Day 3 (Wednesday):**
- Scrapes 0 new jobs → Nothing added
- Emails you nothing (no new jobs added today)

## Database Fields

- `created_at` - When the job was added to YOUR database (today's date when scraped)
- `date_posted` - When the job was posted on the job board (from the website)
- `emailed` - 'yes' or 'no' - Whether you've been emailed about this job
- `emailed_date` - When the job was emailed to you

## Testing

To test the email with real jobs:
```bash
# First, scrape some jobs
python main.py

# Then test email (will use jobs added today)
python test_email.py
```

The test script will automatically find jobs added to the database today and use those for the email.


