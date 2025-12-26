"""
Test script to verify job title filtering works correctly
"""
import sys
from pathlib import Path

# Add parent directory to path so we can import from root
sys.path.insert(0, str(Path(__file__).parent.parent))

import config
from main import should_exclude_job, filter_jobs


def test_filter():
    """Test the job title filter"""
    print("=" * 60)
    print("Testing Job Title Filter")
    print("=" * 60)
    print()
    
    # Show configured keywords
    exclude_keywords = getattr(config, 'EXCLUDE_TITLE_KEYWORDS', [])
    print(f"Configured exclude keywords: {exclude_keywords}")
    print()
    
    # Test cases
    test_jobs = [
        {
            'title': 'Software Engineer',
            'location': 'San Diego, CA',
            'description': 'Entry level software engineer position'
        },
        {
            'title': 'Senior Software Engineer',
            'location': 'San Diego, CA',
            'description': 'Senior level position'
        },
        {
            'title': 'Sr. Software Developer',
            'location': 'Remote',
            'description': 'Senior developer role'
        },
        {
            'title': 'Engineering Manager',
            'location': 'Toronto, ON',
            'description': 'Management position'
        },
        {
            'title': 'Staff Engineer',
            'location': 'Austin, TX',
            'description': 'Staff level engineer'
        },
        {
            'title': 'Principal Software Engineer',
            'location': 'Seattle, WA',
            'description': 'Principal level role'
        },
        {
            'title': 'Software Engineer II',
            'location': 'Boston, MA',
            'description': 'Mid-level engineer'
        },
        {
            'title': 'Junior Software Engineer',
            'location': 'New York, NY',
            'description': 'Junior level position'
        },
    ]
    
    print("Testing individual jobs:")
    print("-" * 60)
    
    for job in test_jobs:
        excluded = should_exclude_job(job)
        status = "EXCLUDED" if excluded else "INCLUDED"
        print(f"{status:10} | {job['title']}")
    
    print()
    print("=" * 60)
    print("Testing filter_jobs function:")
    print("=" * 60)
    
    filtered_jobs, excluded_count = filter_jobs(test_jobs)
    
    print(f"\nTotal jobs tested: {len(test_jobs)}")
    print(f"Jobs excluded: {excluded_count}")
    print(f"Jobs included: {len(filtered_jobs)}")
    print()
    
    print("Included jobs:")
    for job in filtered_jobs:
        print(f"  [OK] {job['title']}")
    
    print()
    print("Excluded jobs:")
    excluded_jobs = [job for job in test_jobs if should_exclude_job(job)]
    for job in excluded_jobs:
        print(f"  [X] {job['title']}")
    
    print()
    print("=" * 60)
    print("Filter Test Complete")
    print("=" * 60)


if __name__ == "__main__":
    test_filter()

