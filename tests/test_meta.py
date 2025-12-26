"""
Test script for Meta scraper
"""
import sys
from pathlib import Path

# Add parent directory to path so we can import from root
sys.path.insert(0, str(Path(__file__).parent.parent))

from scrapers.meta_scraper import MetaScraper

def test_meta_scraper():
    """Test the Meta scraper"""
    print("=" * 70)
    print("Testing Meta Scraper")
    print("=" * 70)
    print()
    
    base_url = "https://www.metacareers.com/jobsearch?roles[0]=Full%20time%20employment&sort_by_new=true&offices[0]=North%20America"
    
    scraper = MetaScraper(base_url)
    
    print(f"Source: {scraper.source_name}")
    print(f"Base URL: {scraper.base_url}")
    print(f"GraphQL URL: {scraper.graphql_url}")
    print()
    
    print("Testing scraper...")
    print("-" * 70)
    print()
    print("NOTE: Meta GraphQL may require authentication or specific query format.")
    print("If GraphQL fails, it will try HTML scraping as fallback.")
    print()
    
    try:
        jobs = scraper.scrape_jobs(filter_today_only=False)  # Don't filter by date
        
        print(f"\nFound {len(jobs)} total jobs\n")
        
        if jobs:
            print("First 10 jobs:")
            for i, job in enumerate(jobs[:10], 1):
                print(f"\n{i}. {job.get('title', 'N/A')}")
                print(f"   Location: {job.get('location', 'N/A')}")
                print(f"   Date Posted: {job.get('date_posted', 'None')}")
                print(f"   URL: {job.get('url', 'N/A')}")
                print(f"   Job ID: {job.get('job_id', 'N/A')}")
        else:
            print("No jobs found. This could mean:")
            print("  - GraphQL API requires authentication")
            print("  - The query format needs adjustment")
            print("  - HTML structure needs adjustment")
    
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_meta_scraper()

