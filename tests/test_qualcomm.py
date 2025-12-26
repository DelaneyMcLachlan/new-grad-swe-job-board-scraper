"""
Test script specifically for Qualcomm scraper
Helps debug and find the correct API endpoints and data structure
"""
import sys
from pathlib import Path

# Add parent directory to path so we can import from root
sys.path.insert(0, str(Path(__file__).parent.parent))

import json
import requests
from bs4 import BeautifulSoup
from scrapers.qualcomm_scraper import QualcommScraper
import re


def test_qualcomm_scraper():
    """Test the Qualcomm scraper"""
    print("=" * 60)
    print("Testing Qualcomm Scraper")
    print("=" * 60)
    print()
    
    base_url = "https://careers.qualcomm.com/careers?location=Canada&pid=446715551519&domain=qualcomm.com&sort_by=relevance"
    scraper = QualcommScraper(base_url)
    
    # Test scraping Canada
    print("Testing Canada location...")
    canada_jobs = scraper._scrape_location("Canada")
    print(f"Found {len(canada_jobs)} jobs from Canada")
    if canada_jobs:
        print("\nSample job:")
        print(json.dumps(canada_jobs[0], indent=2, default=str))
    
    print("\n" + "-" * 60 + "\n")
    
    # Test scraping United States
    print("Testing United States location...")
    us_jobs = scraper._scrape_location("United States")
    print(f"Found {len(us_jobs)} jobs from United States")
    if us_jobs:
        print("\nSample job:")
        print(json.dumps(us_jobs[0], indent=2, default=str))
    
    print("\n" + "-" * 60 + "\n")
    
    # Test scraping both
    print("Testing both locations...")
    all_jobs = scraper.scrape_jobs(locations=["Canada", "United States"])
    print(f"Found {len(all_jobs)} total jobs")
    
    # Show summary
    if all_jobs:
        print("\nJob Summary:")
        locations = {}
        for job in all_jobs:
            loc = job.get('location', 'Unknown')
            locations[loc] = locations.get(loc, 0) + 1
        
        for loc, count in locations.items():
            print(f"  {loc}: {count} jobs")


def inspect_page_structure():
    """Inspect the actual page structure to help find the right selectors"""
    print("\n" + "=" * 60)
    print("Inspecting Qualcomm Page Structure")
    print("=" * 60)
    print()
    
    url = "https://careers.qualcomm.com/careers?location=Canada&pid=446715551519&domain=qualcomm.com&sort_by=relevance"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        print(f"Status Code: {response.status_code}")
        print(f"Content Length: {len(response.content)} bytes")
        print()
        
        soup = BeautifulSoup(response.content, 'lxml')
        
        # Look for script tags with JSON
        print("Looking for JSON data in script tags...")
        script_tags = soup.find_all('script')
        json_scripts = []
        for i, script in enumerate(script_tags):
            if script.string and ('position' in script.string.lower() or 'job' in script.string.lower()):
                json_scripts.append((i, len(script.string), script.string[:200]))
        
        print(f"Found {len(json_scripts)} potentially relevant script tags")
        for idx, length, preview in json_scripts[:5]:
            print(f"  Script {idx}: {length} chars - {preview}...")
        
        # Look for API endpoints in the page
        print("\nLooking for API endpoints...")
        page_text = response.text
        api_patterns = [
            r'https?://[^"\s]+api[^"\s]+',
            r'https?://[^"\s]+eightfold[^"\s]+',
            r'/api/[^"\s]+',
        ]
        
        found_apis = set()
        for pattern in api_patterns:
            matches = re.findall(pattern, page_text)
            found_apis.update(matches)
        
        print(f"Found {len(found_apis)} potential API endpoints:")
        for api in list(found_apis)[:10]:
            print(f"  {api}")
        
        # Look for job-related HTML elements
        print("\nLooking for job-related HTML elements...")
        job_elements = soup.find_all(attrs={'class': re.compile(r'job|position|card', re.I)})
        print(f"Found {len(job_elements)} elements with job/position/card in class")
        
        # Check for data attributes
        data_attrs = soup.find_all(attrs={'data-position-id': True})
        data_attrs.extend(soup.find_all(attrs={'data-job-id': True}))
        print(f"Found {len(data_attrs)} elements with data-position-id or data-job-id")
        
    except Exception as e:
        print(f"Error inspecting page: {e}")


if __name__ == "__main__":
    print("Choose an option:")
    print("1. Test Qualcomm scraper")
    print("2. Inspect page structure (for debugging)")
    print("3. Both")
    
    choice = input("\nEnter choice (1-3): ").strip()
    
    if choice == "1":
        test_qualcomm_scraper()
    elif choice == "2":
        inspect_page_structure()
    elif choice == "3":
        inspect_page_structure()
        test_qualcomm_scraper()
    else:
        print("Invalid choice. Running both tests...")
        inspect_page_structure()
        test_qualcomm_scraper()


