"""
Main script to orchestrate job scraping, database storage, and email notifications
"""
import sys
from datetime import datetime, timedelta
from database import Database
from scrapers.scraper_factory import ScraperFactory
from email_sender import EmailSender
import config


def should_exclude_job(job_data):
    """
    Check if a job should be excluded based on title keywords.
    Applies to ALL job boards automatically.
    
    Args:
        job_data: Dictionary containing job information with 'title' key
    
    Returns:
        True if job should be excluded, False otherwise
    """
    title = job_data.get('title', '')
    if not title:
        return False
    
    # Get exclude keywords from config (default to empty list if not set)
    exclude_keywords = getattr(config, 'EXCLUDE_TITLE_KEYWORDS', [])
    
    if not exclude_keywords:
        return False
    
    # Case-insensitive check - check if any keyword appears in the title
    title_lower = title.lower()
    for keyword in exclude_keywords:
        if keyword.lower() in title_lower:
            return True
    
    return False


def filter_jobs(jobs):
    """
    Filter out jobs that match exclusion criteria.
    
    Args:
        jobs: List of job dictionaries
    
    Returns:
        Tuple of (filtered_jobs, excluded_count)
    """
    filtered_jobs = []
    excluded_count = 0
    
    for job in jobs:
        if should_exclude_job(job):
            excluded_count += 1
        else:
            filtered_jobs.append(job)
    
    return filtered_jobs, excluded_count


def scrape_all_boards():
    """
    Scrape all configured job boards and store results in database.
    All jobs are scraped (no date filtering).
    Database handles duplicates - only new jobs are added.
    Email will send only jobs added to database today.
    """
    db = Database()
    all_new_jobs = []
    
    print(f"Starting job scraping at {datetime.now()}")
    print(f"Scraping {len(config.JOB_BOARDS)} job board(s)...\n")
    
    for board_name, base_url in config.JOB_BOARDS.items():
        print(f"Scraping {board_name}...")
        scraper = ScraperFactory.create_scraper(board_name, base_url)
        
        if not scraper:
            print(f"  Skipping {board_name} - no scraper available\n")
            continue
        
        # Display API endpoint/URL being used
        api_info = None
        if hasattr(scraper, 'api_endpoint'):
            api_info = scraper.api_endpoint
        elif hasattr(scraper, 'api_base'):
            api_info = scraper.api_base
        elif hasattr(scraper, 'graphql_url'):
            api_info = scraper.graphql_url
        elif hasattr(scraper, 'base_url'):
            api_info = scraper.base_url
        
        if api_info:
            print(f"  API Endpoint: {api_info}")
        
        try:
            # Check if this board has location configuration
            locations = config.JOB_BOARD_LOCATIONS.get(board_name)
            
            # Scrape all jobs (no date filtering - database handles duplicates)
            if locations:
                # Pass locations to scraper if it supports it
                jobs = scraper.scrape_jobs(locations=locations, filter_today_only=False)
            else:
                # Scrape all jobs
                jobs = scraper.scrape_jobs(filter_today_only=False)
            
            print(f"  Found {len(jobs)} total jobs")
            
            # Filter out jobs based on title keywords (applies to all job boards)
            filtered_jobs, excluded_count = filter_jobs(jobs)
            if excluded_count > 0:
                exclude_keywords = getattr(config, 'EXCLUDE_TITLE_KEYWORDS', [])
                keywords_str = ', '.join(exclude_keywords) if exclude_keywords else 'configured keywords'
                print(f"  Excluded {excluded_count} job(s) containing: {keywords_str}")
            
            # Add jobs to database (only adds if job doesn't already exist)
            new_count = 0
            duplicate_count = 0
            for job_data in filtered_jobs:
                job_data['source'] = board_name
                if db.add_job(job_data):
                    new_count += 1
                    all_new_jobs.append(job_data)
                else:
                    duplicate_count += 1
            
            print(f"  Added {new_count} new jobs to database")
            if duplicate_count > 0:
                print(f"  Skipped {duplicate_count} duplicate job(s) (already in database)")
            print()
            
        except Exception as e:
            print(f"  Error scraping {board_name}: {e}\n")
            continue
    
    db.close()
    return all_new_jobs


def send_daily_email():
    """
    Get new jobs added to database today and send email notification.
    Only jobs that were added to the database during today's scraping run
    will be included. The database tracks duplicates, so only truly new jobs
    are added and emailed.
    """
    db = Database()
    email_sender = EmailSender()
    
    # Get jobs that were added to database TODAY and haven't been emailed yet
    # This ensures we only email jobs from today's scraping run
    new_jobs = db.get_today_new_jobs()
    
    if new_jobs:
        print(f"Found {len(new_jobs)} new jobs added today to email")
        
        # Show breakdown by source
        jobs_by_source = {}
        for job in new_jobs:
            source = job.source
            jobs_by_source[source] = jobs_by_source.get(source, 0) + 1
        
        for source, count in jobs_by_source.items():
            print(f"  {source}: {count} job(s)")
        
        # Send email
        if email_sender.send_jobs_email(new_jobs):
            # Mark jobs as emailed so they won't be sent again
            job_ids = [job.job_id for job in new_jobs]
            db.mark_as_emailed(job_ids)
            print(f"\nSuccessfully emailed {len(new_jobs)} job(s)")
            print("Jobs marked as emailed - they won't be sent again")
        else:
            print("\nFailed to send email - jobs NOT marked as emailed")
            print("  They will be included in the next email attempt")
    else:
        print("No new jobs to email (no jobs were added to database today)")
    
    db.close()


def main():
    """Main entry point"""
    if len(sys.argv) > 1 and sys.argv[1] == '--email-only':
        # Only send email for existing new jobs
        send_daily_email()
    else:
        # Scrape and then send email
        scrape_all_boards()
        send_daily_email()
    
    print(f"\nCompleted at {datetime.now()}")


if __name__ == "__main__":
    main()

