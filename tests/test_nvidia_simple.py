"""
Simple test for NVIDIA Workday scraper - only jobs posted today
Returns JSON output
"""
import sys
from pathlib import Path

# Add parent directory to path so we can import from root
sys.path.insert(0, str(Path(__file__).parent.parent))

import json
from scrapers.workday_scraper import WorkdayScraper

def main():
    """Test NVIDIA scraper - only jobs posted today"""
    print("=" * 70)
    print("NVIDIA Workday Scraper - Jobs Posted Today Only")
    print("=" * 70)
    print()
    
    # Base URL without filters
    base_url = "https://nvidia.wd5.myworkdayjobs.com/NVIDIAExternalCareerSite"
    
    scraper = WorkdayScraper(base_url)
    
    print(f"Company: {scraper.company_name}")
    print(f"API Endpoint: {scraper.api_endpoint}")
    print()
    print("Scraping jobs posted today only...")
    print("-" * 70)
    print()
    
    try:
        # Get jobs posted today only
        jobs = scraper.scrape_jobs(filter_today_only=True)
        
        print(f"Found {len(jobs)} job(s) posted today\n")
        
        if jobs:
            # Show summary
            print("Jobs found:")
            for i, job in enumerate(jobs, 1):
                print(f"  {i}. {job.get('title', 'N/A')}")
                print(f"     Location: {job.get('location', 'N/A')}")
                print(f"     Date: {job.get('date_posted_raw', 'N/A')}")
                print(f"     URL: {job.get('url', 'N/A')}")
                print()
            
            # Output as JSON
            print("=" * 70)
            print("JSON OUTPUT:")
            print("=" * 70)
            print(json.dumps(jobs, indent=2, default=str))
            
            # Save to file
            output_file = "nvidia_jobs_today.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(jobs, f, indent=2, default=str)
            print(f"\nSaved to: {output_file}")
        else:
            print("No jobs posted today found.")
            print("\nThis could mean:")
            print("  - No new jobs were posted today")
            print("  - All jobs have different date formats")
    
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

