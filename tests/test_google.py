"""
Test script for Google scraper
"""
import sys
from pathlib import Path

# Add parent directory to path so we can import from root
sys.path.insert(0, str(Path(__file__).parent.parent))

from scrapers.google_scraper import GoogleScraper

def test_google_scraper():
    """Test the Google scraper"""
    print("=" * 70)
    print("Testing Google Scraper")
    print("=" * 70)
    print()
    
    base_url = "https://www.google.com/about/careers/applications/jobs/results?location=United%20States&location=Canada&target_level=MID&target_level=INTERN_AND_APPRENTICE&target_level=EARLY&sort_by=date&employment_type=FULL_TIME"
    
    scraper = GoogleScraper(base_url)
    
    print(f"Source: {scraper.source_name}")
    print(f"Base URL: {scraper.base_url}")
    print()
    
    print("Testing scraper...")
    print("-" * 70)
    print()
    
    try:
        jobs = scraper.scrape_jobs(filter_today_only=False)
        
        print(f"\nFound {len(jobs)} total jobs\n")
        
        if jobs:
            print("First 10 jobs:")
            for i, job in enumerate(jobs[:10], 1):
                print(f"\n{i}. {job.get('title', 'N/A')}")
                print(f"   Location: {job.get('location', 'N/A')}")
                print(f"   URL: {job.get('url', 'N/A')}")
                print(f"   Job ID: {job.get('job_id', 'N/A')}")
        else:
            print("No jobs found. This could mean:")
            print("  - The HTML structure needs adjustment")
            print("  - The JavaScript extraction needs improvement")
    
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_google_scraper()

