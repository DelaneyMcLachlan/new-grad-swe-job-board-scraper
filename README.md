# Job Board Scraper

A web scraper for multiple software engineering job boards that collects job listings, stores them in a database, and sends daily email notifications of new jobs.

## Features

- **Multi-board scraping**: Scrape multiple job boards with a modular architecture
- **Database storage**: SQLite database to track all jobs and prevent duplicates
- **Email notifications**: Daily email with new job listings
- **Duplicate prevention**: Automatically filters out jobs already in the database
- **VM-ready**: Designed to run on a schedule in a virtual machine

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Email Settings

Copy `.env.example` to `.env` and fill in your email settings:

```bash
cp .env.example .env
```

Edit `.env` with your email credentials:
- For Gmail, use an [App Password](https://myaccount.google.com/apppasswords) instead of your regular password
- Set `EMAIL_TO` to the address where you want to receive job notifications

### 3. Configure Job Boards

Edit `config.py` and add your job board URLs to the `JOB_BOARDS` dictionary:

```python
JOB_BOARDS = {
    "indeed": "https://www.indeed.com/jobs?q=software+engineer&l=",
    "linkedin": "https://www.linkedin.com/jobs/search/?keywords=software%20engineer",
    # Add more job boards here
}
```

### 4. Configure Job Title Filters (Optional)

Edit `config.py` to exclude jobs based on title keywords. This applies to ALL job boards automatically:

```python
EXCLUDE_TITLE_KEYWORDS = [
    "Senior",
    "Sr",
    "Manager",
    "Staff",
    "Principal",
]
```

Jobs containing any of these words (case-insensitive) in the title will be excluded from the database and emails.

### 5. Create Job Board Scrapers

Each job board needs its own scraper implementation. See `scrapers/qualcomm_scraper.py` or `scrapers/workday_scraper.py` for examples.

To create a new scraper:

1. Create a new scraper file (e.g., `scrapers/indeed_scraper.py`) based on existing scrapers
2. Implement the `scrape_jobs()` method based on the job board's HTML/JSON structure
3. Register it in `scrapers/scraper_factory.py`:

```python
from .indeed_scraper import IndeedScraper

_scrapers = {
    'indeed': IndeedScraper,
    # ... other scrapers
}
```

## Usage

### Run Once

```bash
python main.py
```

This will:
1. Scrape all configured job boards
2. Store new jobs in the database
3. Send an email with jobs found in the last 24 hours

### Send Email Only (for existing new jobs)

```bash
python main.py --email-only
```

### Schedule Daily Runs (Cloud Deployment - Recommended)

Since you need this to run without your laptop being on, deploy to a cloud service:

**Easiest Option: PythonAnywhere (Free tier available)**
- See `pythonanywhere_setup.md` for detailed instructions
- Free tier allows daily scheduled tasks
- No command line knowledge required

**Other Options:**
- AWS Lambda + EventBridge (see `DEPLOYMENT_GUIDE.md`)
- Railway.app
- Render.com
- DigitalOcean

See `DEPLOYMENT_GUIDE.md` for all deployment options.

### Schedule Daily Runs (Local - Requires Laptop On)

**Linux/Mac (crontab):**
```bash
crontab -e
```
Add this line to run daily at 9 AM:
```
0 9 * * * cd /path/to/project && /usr/bin/python3 main.py
```

**Windows Task Scheduler:**
1. Open Task Scheduler
2. Create Basic Task
3. Set trigger to "Daily" at your preferred time
4. Set action to "Start a program"
5. Program: `python`
6. Arguments: `C:\path\to\project\main.py`
7. Start in: `C:\path\to\project`

**Note:** Local scheduling requires your computer to be on at the scheduled time.

## Project Structure

```
.
├── main.py                 # Main orchestrator script
├── config.py              # Configuration settings
├── database.py            # Database models and operations
├── email_sender.py        # Email notification functionality
├── requirements.txt       # Python dependencies
├── .env.example          # Example environment variables
├── jobs.db               # SQLite database (created automatically)
└── scrapers/
    ├── __init__.py
    ├── base_scraper.py   # Base class for all scrapers
    └── scraper_factory.py # Factory for creating scrapers
```

## Database Schema

The `jobs` table stores:
- `id`: Auto-increment primary key
- `job_id`: Unique identifier for the job (indexed)
- `title`: Job title
- `location`: Job location
- `description`: Job description
- `date_posted`: When the job was posted
- `source`: Which job board it came from
- `url`: Link to the job posting
- `created_at`: When it was added to database
- `emailed`: Whether it's been emailed ('yes' or 'no')
- `emailed_date`: When it was emailed

## Creating a New Scraper

Each job board has a different structure, so you'll need to create a custom scraper. Here's a quick guide:

1. **Inherit from BaseScraper**: Your scraper should inherit from `scrapers.base_scraper.BaseScraper`

2. **Implement scrape_jobs()**: This method should return a list of dictionaries with these keys:
   - `job_id`: Unique identifier (string)
   - `title`: Job title (string)
   - `location`: Location (string, optional)
   - `description`: Job description (string, optional)
   - `date_posted`: datetime object (optional)
   - `url`: Link to job posting (string, optional)

3. **Use helper methods**: 
   - `self.fetch_page(url)` - Fetches a page with rate limiting (GET request)
   - `self.fetch_page(url, method='POST', json_data={})` - For POST requests (e.g., Workday API)
   - `self.parse_date(date_string)` - Parses date strings

4. **Register your scraper**: Add it to `scraper_factory.py`

### Workday Job Boards

If you're adding a company that uses Workday (like NVIDIA, Apple, etc.), you can use the generic `WorkdayScraper`:

```python
# In config.py
JOB_BOARDS = {
    "nvidia": "https://nvidia.wd5.myworkdayjobs.com/NVIDIAExternalCareerSite?...",
    "apple": "https://apple.wd5.myworkdayjobs.com/AppleExternalCareerSite?...",
    # Just use "workday" or company name as the key
}

# The scraper factory will auto-detect Workday URLs
# Or explicitly use "workday" as the key
```

The `WorkdayScraper` automatically:
- Extracts company name and site from URL
- Constructs the API endpoint
- Handles pagination
- Parses Workday's JSON response format

## Notes

- The scraper includes a 2-second delay between requests to be respectful to servers
- Jobs are stored permanently in the database, but only new jobs are emailed
- The same job won't be emailed twice (tracked by `job_id`)
- Make sure to respect robots.txt and terms of service for each job board

## Troubleshooting

**Email not sending:**
- Check your `.env` file has correct credentials
- For Gmail, make sure you're using an App Password
- Check firewall/network settings

**Scraper not finding jobs:**
- Job board HTML structure may have changed
- Check the selectors in your scraper match the current HTML
- Some sites may require JavaScript rendering (consider Selenium)

**Database errors:**
- Make sure you have write permissions in the project directory
- Delete `jobs.db` to start fresh (you'll lose all stored jobs)

## Future Enhancements

- Add support for JavaScript-rendered sites (Selenium/Playwright)
- Add filtering by keywords, location, salary range
- Add web dashboard to view jobs
- Support for more job boards
- Export jobs to CSV/JSON

