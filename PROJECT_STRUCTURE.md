# Project Structure

This document describes the organization of the job scraper project.

## Directory Structure

```
CursorProjects/
├── main.py                 # Main entry point - run this to scrape and email jobs
├── config.py               # Configuration file (job boards, filters, etc.)
├── database.py             # Database models and operations
├── email_sender.py         # Email notification functionality
├── requirements.txt        # Python dependencies
├── README.md               # Main documentation
├── jobs.db                 # SQLite database (auto-created)
│
├── scrapers/               # Job board scrapers
│   ├── __init__.py
│   ├── base_scraper.py     # Base class for all scrapers
│   ├── scraper_factory.py  # Factory to create scrapers
│   ├── qualcomm_scraper.py # Qualcomm job board scraper
│   └── workday_scraper.py  # Generic Workday scraper (used for NVIDIA, etc.)
│
├── utils/                  # Utility scripts
│   ├── __init__.py
│   └── view_database.py    # View database contents
│
└── tests/                  # Test scripts
    ├── __init__.py
    ├── test_setup.py       # Test overall setup
    ├── test_env.py         # Test environment variables
    ├── test_filter.py      # Test job filtering
    ├── test_qualcomm.py    # Test Qualcomm scraper
    └── test_nvidia_simple.py # Test NVIDIA scraper
```

## Key Files

### Main Application
- **main.py** - Run `python main.py` to scrape jobs and send emails
- **config.py** - Configure job boards, filters, and email settings
- **database.py** - Database operations (SQLite)
- **email_sender.py** - Email functionality

### Scrapers
- **scrapers/base_scraper.py** - Base class that all scrapers inherit from
- **scrapers/scraper_factory.py** - Creates appropriate scraper instances
- **scrapers/qualcomm_scraper.py** - Scrapes Qualcomm job board
- **scrapers/workday_scraper.py** - Generic scraper for Workday job boards (NVIDIA, etc.)

### Utilities
- **utils/view_database.py** - View jobs in database
  - Run: `python utils/view_database.py`
  - Options: `--summary`, `--recent [N]`

### Tests
- **tests/test_setup.py** - Verify setup is working
- **tests/test_env.py** - Check environment variables
- **tests/test_filter.py** - Test job filtering logic
- **tests/test_qualcomm.py** - Test Qualcomm scraper
- **tests/test_nvidia_simple.py** - Test NVIDIA scraper

## Usage

### Daily Scraping
```bash
python main.py
```

### View Database
```bash
python utils/view_database.py          # View all jobs
python utils/view_database.py --summary # Quick summary
python utils/view_database.py --recent 5 # Recent 5 jobs
```

### Run Tests
```bash
python tests/test_setup.py      # Test overall setup
python tests/test_env.py         # Test environment
python tests/test_filter.py      # Test filtering
python tests/test_nvidia_simple.py # Test NVIDIA scraper
```

## Adding New Job Boards

1. Create a new scraper in `scrapers/` (inherit from `BaseScraper`)
2. Register it in `scrapers/scraper_factory.py`
3. Add the URL to `config.py` in `JOB_BOARDS`

