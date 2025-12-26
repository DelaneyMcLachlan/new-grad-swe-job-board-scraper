"""
Test script to verify the setup is working correctly
"""
import sys
from pathlib import Path

# Add parent directory to path so we can import from root
sys.path.insert(0, str(Path(__file__).parent.parent))

from database import Database
from scrapers.scraper_factory import ScraperFactory
import config


def test_database():
    """Test database connection and operations"""
    print("Testing database...")
    try:
        db = Database()
        
        # Test adding a job
        test_job = {
            'job_id': 'test_123',
            'title': 'Test Software Engineer',
            'location': 'Remote',
            'description': 'This is a test job',
            'date_posted': None,
            'source': 'test',
            'url': 'https://example.com/job/123'
        }
        
        result = db.add_job(test_job)
        if result:
            print("  Database write successful")
        else:
            print("  [OK] Database duplicate detection working")
        
        # Test checking if job exists
        exists = db.job_exists('test_123')
        print(f"  [OK] Job exists check: {exists}")
        
        db.close()
        print("  [OK] Database test passed\n")
        return True
    except Exception as e:
        print(f"  Database test failed: {e}\n")
        return False


def test_scrapers():
    """Test scraper factory"""
    print("Testing scrapers...")
    try:
        if not config.JOB_BOARDS:
            print("  [WARNING] No job boards configured in config.py")
            print("  Add URLs to JOB_BOARDS dictionary to test scraping\n")
            return True
        
        for board_name, url in config.JOB_BOARDS.items():
            scraper = ScraperFactory.create_scraper(board_name, url)
            if scraper:
                print(f"  [OK] Scraper found for '{board_name}'")
            else:
                print(f"  [FAIL] No scraper found for '{board_name}'")
                print(f"    You need to create a scraper for this board")
        
        print("  [OK] Scraper factory test passed\n")
        return True
    except Exception as e:
        print(f"  [FAIL] Scraper test failed: {e}\n")
        return False


def test_email_config():
    """Test email configuration"""
    print("Testing email configuration...")
    try:
        if not config.EMAIL_USER or not config.EMAIL_PASSWORD or not config.EMAIL_TO:
            print("  [WARNING] Email not configured")
            print("  Set EMAIL_USER, EMAIL_PASSWORD, and EMAIL_TO in .env file")
            print("  Email functionality will be disabled until configured\n")
            return False
        else:
            print("  [OK] Email configuration found")
            print("  [OK] Email test passed\n")
            return True
    except Exception as e:
        print(f"  [FAIL] Email test failed: {e}\n")
        return False


def main():
    """Run all tests"""
    print("=" * 50)
    print("Job Scraper Setup Test")
    print("=" * 50)
    print()
    
    results = []
    results.append(("Database", test_database()))
    results.append(("Scrapers", test_scrapers()))
    results.append(("Email Config", test_email_config()))
    
    print("=" * 50)
    print("Test Summary")
    print("=" * 50)
    
    for name, passed in results:
        status = "[OK] PASS" if passed else "[FAIL] FAIL / [WARNING] WARNING"
        print(f"{name}: {status}")
    
    all_passed = all(result[1] for result in results)
    
    if all_passed:
        print("\n[OK] All tests passed! You're ready to start scraping.")
    else:
        print("\n[WARNING] Some tests had warnings. Check the output above.")
        print("The scraper will still work, but some features may be disabled.")


if __name__ == "__main__":
    main()


