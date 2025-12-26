"""
Configuration file for job scraper
"""
import os
from dotenv import load_dotenv

load_dotenv()

# Database configuration
DATABASE_PATH = "jobs.db"

# Email configuration (set these in .env file)
EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_USER = os.getenv("EMAIL_USER", "")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "")
EMAIL_TO = os.getenv("EMAIL_TO", "")

# Job board URLs - Add your URLs here
JOB_BOARDS = {
    "qualcomm": "https://careers.qualcomm.com/careers?location=Canada&pid=446715551519&domain=qualcomm.com&sort_by=relevance",
    "nvidia": "https://nvidia.wd5.myworkdayjobs.com/NVIDIAExternalCareerSite",  # Base URL - will get all jobs
    "cadence": "https://cadence.wd1.myworkdayjobs.com/en-US/External_Careers?timeType=59ec2ade908946248e84acbf58584a93&Location_Country=a30a87ed25634629aa6c3958aa2b91ea&Location_Country=bc33aa3152ec42d4995f4791a106ed09",  # Workday with filters
    "google": "https://www.google.com/about/careers/applications/jobs/results?location=United%20States&location=Canada&target_level=MID&target_level=INTERN_AND_APPRENTICE&target_level=EARLY&sort_by=date&employment_type=FULL_TIME",
    "amd": "https://careers.amd.com/careers-home/jobs?country=United%20States%7CCanada&page=1&sortBy=posted_date&descending=true",
    "synopsys": "https://careers.synopsys.com/category/engineering-jobs/44408/8675488/1",  # Engineering jobs
    "meta": "https://www.metacareers.com/jobsearch?roles[0]=Full%20time%20employment&sort_by_new=true&offices[0]=North%20America",
    # Example: "indeed": "https://www.indeed.com/jobs?q=software+engineer&l=",
    # Add your job board URLs here
    # For Workday job boards, use "workday" or company name as key
}

# Job board locations - Specify which locations to scrape for each board
# Leave empty or omit to use defaults from URL or scraper
JOB_BOARD_LOCATIONS = {
    "qualcomm": ["Canada", "United States"],  # Scrape both Canada and US jobs
    # Add more board-specific location configurations here
}

# Scraper settings
SCRAPER_DELAY_SECONDS = 2  # Delay between requests to be respectful
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
FILTER_TODAY_ONLY = False  # Scrape all jobs - database handles duplicates, email sends only new ones

# Job title filter - Jobs containing these words in the title will be excluded
# Applies to ALL job boards automatically
# Case-insensitive matching (e.g., "Senior" matches "senior", "SENIOR", "Senior Engineer")
EXCLUDE_TITLE_KEYWORDS = [
    "Senior",
    "Sr",
    "Manager",
    "Staff",
    "Principal",
    "Executive",
    "Director",
    "Chief",
]

