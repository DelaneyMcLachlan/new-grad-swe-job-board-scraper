"""
Test script for Texas Instruments scraper
"""
import sys
from pathlib import Path

# Add parent directory to path so we can import from root
sys.path.insert(0, str(Path(__file__).parent.parent))

from scrapers.ti_scraper import TIScraper

def test_ti_scraper():
    """Test the Texas Instruments scraper"""
    print("=" * 70)
    print("Testing Texas Instruments Scraper")
    print("=" * 70)
    print()
    
    base_url = "https://careers.ti.com/en/sites/CX/jobs?sortBy=POSTING_DATES_DESC"
    
    scraper = TIScraper(base_url)
    
    print(f"Source: {scraper.source_name}")
    print(f"Base URL: {scraper.base_url}")
    print(f"Site Code: {scraper.site_code}")
    print()
    
    print("Testing scraper (filter_today_only=True)...")
    print("-" * 70)
    print()
    
    try:
        jobs = scraper.scrape_jobs(filter_today_only=True)
        
        print(f"\nFound {len(jobs)} job(s) posted today\n")
        
        if jobs:
            print("Jobs found:")
            for i, job in enumerate(jobs[:10], 1):
                print(f"\n{i}. {job.get('title', 'N/A')}")
                print(f"   Location: {job.get('location', 'N/A')}")
                print(f"   Date Posted: {job.get('date_posted', 'N/A')}")
                print(f"   URL: {job.get('url', 'N/A')}")
                print(f"   Job ID: {job.get('job_id', 'N/A')}")
        else:
            print("No jobs found. This could mean:")
            print("  - No jobs were posted today")
            print("  - The HTML structure needs adjustment")
            print("  - The site uses JavaScript to load jobs")
            print("  - The API endpoint needs authentication")
            print("\nTrying without date filter to see if scraper works...")
            print("-" * 70)
            jobs_all = scraper.scrape_jobs(filter_today_only=False)
            print(f"\nFound {len(jobs_all)} total jobs")
            if jobs_all:
                print("\nSample jobs:")
                for i, job in enumerate(jobs_all[:5], 1):
                    print(f"\n{i}. {job.get('title', 'N/A')}")
                    print(f"   Location: {job.get('location', 'N/A')}")
                    print(f"   Date Posted: {job.get('date_posted', 'N/A')}")
                    print(f"   URL: {job.get('url', 'N/A')}")
    
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_ti_scraper()

