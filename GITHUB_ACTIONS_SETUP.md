# GitHub Actions Setup Guide

This guide will help you set up automated daily runs of your job scraper using GitHub Actions (100% free for public repositories).

## Why GitHub Actions?

- ✅ **100% Free** for public repositories
- ✅ **No credit card required**
- ✅ **No external service signup needed**
- ✅ **Runs automatically every day**
- ✅ **Can trigger manually from GitHub UI**
- ✅ **Runs in the cloud** (your computer doesn't need to be on)

## Setup Steps

### 1. Add Secrets to GitHub Repository

Your email credentials need to be stored as "Secrets" in GitHub (they're encrypted and never exposed):

1. Go to your repository on GitHub: `https://github.com/YOUR_USERNAME/new-grad-swe-job-board-scraper`
2. Click **Settings** (top menu)
3. Click **Secrets and variables** → **Actions** (left sidebar)
4. Click **New repository secret** and add these three secrets:

   **Secret 1: EMAIL_USER**
   - Name: `EMAIL_USER`
   - Value: Your Gmail address (e.g., `yourname@gmail.com`)

   **Secret 2: EMAIL_PASSWORD**
   - Name: `EMAIL_PASSWORD`
   - Value: Your Gmail App Password (see [GMAIL_SETUP.md](GMAIL_SETUP.md) if you need to create one)

   **Secret 3: EMAIL_TO** (optional)
   - Name: `EMAIL_TO`
   - Value: Email address to receive notifications (defaults to EMAIL_USER if not set)

### 2. Verify Workflow File

The workflow file is already created at `.github/workflows/daily_scraper.yml`. It's configured to:
- Run daily at 9:00 AM UTC
- Install dependencies automatically
- Run your scraper
- Backup the database as an artifact

### 3. Adjust Schedule (Optional)

To change when it runs, edit `.github/workflows/daily_scraper.yml`:

```yaml
- cron: '0 9 * * *'  # 9:00 AM UTC daily
```

Cron format: `minute hour day month weekday`

**Examples:**
- `'0 9 * * *'` = 9:00 AM UTC daily
- `'0 14 * * *'` = 2:00 PM UTC (9:00 AM EST / 6:00 AM PST)
- `'0 0 * * *'` = Midnight UTC daily
- `'0 9 * * 1-5'` = 9:00 AM UTC, weekdays only

**Time Zone Reference:**
- EST = UTC-5 (so 9:00 AM EST = 14:00 UTC)
- PST = UTC-8 (so 9:00 AM PST = 17:00 UTC)
- Use [crontab.guru](https://crontab.guru) to help with cron syntax

### 4. Commit and Push

```bash
git add .github/workflows/daily_scraper.yml
git commit -m "Add GitHub Actions workflow for daily scraping"
git push
```

### 5. Test the Workflow

After pushing, you can test it immediately:

1. Go to your repository on GitHub
2. Click **Actions** tab (top menu)
3. You should see "Daily Job Scraper" workflow
4. Click on it, then click **Run workflow** → **Run workflow** button
5. Watch it run in real-time!

### 6. Monitor Runs

- Go to **Actions** tab to see all workflow runs
- Green checkmark = success
- Red X = failure (check logs for errors)
- Each run shows logs, timing, and results

## How It Works

1. **GitHub Actions** runs your workflow on a schedule (daily at 9 AM UTC)
2. It spins up a fresh Ubuntu virtual machine
3. Installs Python and your dependencies
4. Runs `python main.py` with your secrets as environment variables
5. Your scraper runs, adds jobs to database, and sends email
6. Database is backed up as an artifact (downloadable for 7 days)

## Manual Triggering

You can also trigger the workflow manually:
1. Go to **Actions** tab
2. Click **Daily Job Scraper**
3. Click **Run workflow** button
4. Select branch (usually `main`)
5. Click **Run workflow**

## Troubleshooting

### Workflow Not Running
- Check that the workflow file is in `.github/workflows/` directory
- Verify the cron syntax is correct
- Check GitHub Actions is enabled (Settings → Actions → General)

### Email Not Sending
- Verify secrets are set correctly (Settings → Secrets and variables → Actions)
- Check workflow logs for error messages
- Make sure Gmail App Password is correct (not your regular password)

### Jobs Not Being Found
- Check workflow logs to see scraper output
- Some job boards may block automated requests
- Consider adding delays or user-agent headers

### Database Not Persisting
- The database is created fresh each run (this is expected)
- Only new jobs found in each run will be emailed
- Database is backed up as an artifact (downloadable for 7 days)

## Viewing Logs

1. Go to **Actions** tab
2. Click on a workflow run
3. Click on **scrape-jobs** job
4. Expand steps to see detailed logs
5. Look for "Run job scraper" step to see your scraper output

## Cost

**GitHub Actions is FREE for public repositories:**
- 2,000 minutes/month free
- Each run takes ~2-5 minutes
- That's ~400-1,000 runs/month (way more than daily!)

For private repositories:
- 500 minutes/month free
- Still plenty for daily runs (~100-250 runs/month)

## Alternative: PythonAnywhere

If you prefer a simpler interface, PythonAnywhere also has a free tier:
- See `pythonanywhere_setup.md` for instructions
- Free tier allows daily scheduled tasks
- More user-friendly interface
- Requires separate signup

## Next Steps

1. ✅ Add secrets to GitHub
2. ✅ Push the workflow file
3. ✅ Test manually
4. ✅ Wait for first scheduled run
5. ✅ Check your email!

Your scraper will now run automatically every day! 🎉

