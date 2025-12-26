"""
Test script for Synopsys scraper
"""
import sys
from pathlib import Path

# Add parent directory to path so we can import from root
sys.path.insert(0, str(Path(__file__).parent.parent))

from scrapers.synopsys_scraper import SynopsysScraper

def test_synopsys_scraper():
    """Test the Synopsys scraper"""
    print("=" * 70)
    print("Testing Synopsys Scraper")
    print("=" * 70)
    print()
    
    base_url = "https://careers.synopsys.com/category/engineering-jobs/44408/8675488/1"
    
    scraper = SynopsysScraper(base_url)
    
    print(f"Source: {scraper.source_name}")
    print(f"Base URL: {scraper.base_url}")
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
    
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_synopsys_scraper()

