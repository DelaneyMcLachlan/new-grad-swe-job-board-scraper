"""
View database contents - see all jobs stored in the database
"""
import sys
from pathlib import Path

# Add parent directory to path so we can import from root
sys.path.insert(0, str(Path(__file__).parent.parent))

from database import Database
from datetime import datetime

def view_database():
    """Display all jobs in the database"""
    from database import Job
    db = Database()
    
    # Get all jobs
    all_jobs = db.session.query(Job).order_by(Job.created_at.desc()).all()
    
    print("=" * 80)
    print("DATABASE CONTENTS")
    print("=" * 80)
    print(f"\nTotal jobs in database: {len(all_jobs)}\n")
    
    if not all_jobs:
        print("Database is empty - no jobs found.")
        db.close()
        return
    
    # Group by source
    jobs_by_source = {}
    for job in all_jobs:
        source = job.source
        if source not in jobs_by_source:
            jobs_by_source[source] = []
        jobs_by_source[source].append(job)
    
    print("Jobs by source:")
    for source, jobs in jobs_by_source.items():
        print(f"  {source}: {len(jobs)} job(s)")
    print()
    
    # Show all jobs
    for i, job in enumerate(all_jobs, 1):
        print("-" * 80)
        print(f"Job #{i}")
        print(f"  ID: {job.id}")
        print(f"  Job ID: {job.job_id}")
        print(f"  Title: {job.title}")
        print(f"  Location: {job.location}")
        print(f"  Source: {job.source}")
        print(f"  URL: {job.url}")
        if job.date_posted:
            if isinstance(job.date_posted, datetime):
                print(f"  Date Posted: {job.date_posted.strftime('%Y-%m-%d')}")
            else:
                print(f"  Date Posted: {job.date_posted}")
        if job.created_at:
            print(f"  Added to DB: {job.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  Emailed: {job.emailed}")
        if job.description:
            desc_preview = job.description[:100] + "..." if len(job.description) > 100 else job.description
            print(f"  Description: {desc_preview}")
        print()
    
    db.close()
    print("=" * 80)


def view_summary():
    """Show a summary of the database"""
    db = Database()
    from database import Job
    
    total = db.session.query(Job).count()
    emailed = db.session.query(Job).filter_by(emailed='yes').count()
    not_emailed = db.session.query(Job).filter_by(emailed='no').count()
    
    # By source
    jobs_by_source = {}
    all_jobs = db.session.query(Job).all()
    for job in all_jobs:
        source = job.source
        jobs_by_source[source] = jobs_by_source.get(source, 0) + 1
    
    # Recent jobs (last 7 days)
    from datetime import timedelta
    week_ago = datetime.now() - timedelta(days=7)
    recent = db.session.query(Job).filter(Job.created_at >= week_ago).count()
    
    print("=" * 80)
    print("DATABASE SUMMARY")
    print("=" * 80)
    print(f"\nTotal jobs: {total}")
    print(f"  Emailed: {emailed}")
    print(f"  Not emailed: {not_emailed}")
    print(f"  Added in last 7 days: {recent}")
    print(f"\nJobs by source:")
    for source, count in sorted(jobs_by_source.items()):
        print(f"  {source}: {count}")
    print()
    
    db.close()


def view_recent_jobs(limit=10):
    """Show most recent jobs"""
    db = Database()
    from database import Job
    
    recent_jobs = db.session.query(Job).order_by(Job.created_at.desc()).limit(limit).all()
    
    print("=" * 80)
    print(f"MOST RECENT {limit} JOBS")
    print("=" * 80)
    print()
    
    for i, job in enumerate(recent_jobs, 1):
        print(f"{i}. {job.title}")
        print(f"   Source: {job.source} | Location: {job.location}")
        print(f"   Added: {job.created_at.strftime('%Y-%m-%d %H:%M:%S')} | Emailed: {job.emailed}")
        print(f"   URL: {job.url}")
        print()
    
    db.close()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == '--summary':
            view_summary()
        elif sys.argv[1] == '--recent':
            limit = int(sys.argv[2]) if len(sys.argv) > 2 else 10
            view_recent_jobs(limit)
        else:
            print("Usage:")
            print("  python view_database.py          - View all jobs")
            print("  python view_database.py --summary - Show summary")
            print("  python view_database.py --recent [N] - Show N most recent jobs (default 10)")
    else:
        view_database()

