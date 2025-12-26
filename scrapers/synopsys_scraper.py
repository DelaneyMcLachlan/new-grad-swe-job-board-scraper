"""
Synopsys Careers scraper
Scrapes job listings from Synopsys career page
"""
import re
from bs4 import BeautifulSoup
from .base_scraper import BaseScraper
from datetime import datetime
from urllib.parse import urlparse, urljoin


class SynopsysScraper(BaseScraper):
    """
    Scraper for Synopsys careers page
    """
    
    def __init__(self, base_url):
        super().__init__("synopsys", base_url)
        # Extract base URL
        parsed_url = urlparse(base_url)
        self.base_domain = f"{parsed_url.scheme}://{parsed_url.netloc}"
        
        # Extract category and other path components
        path_parts = parsed_url.path.strip('/').split('/')
        # URL format: /category/engineering-jobs/44408/8675488/1
        # We'll use the base path for pagination
        if len(path_parts) >= 4:
            self.category_path = '/'.join(path_parts[:4])  # /category/engineering-jobs/44408/8675488
    
    def scrape_jobs(self, filter_today_only=True, **kwargs):
        """
        Scrape jobs from Synopsys career page
        
        Args:
            filter_today_only: If True, only return jobs posted today
        
        Returns:
            list: List of job dictionaries
        """
        jobs = []
        
        try:
            page = 1
            max_pages = 10  # Limit to prevent infinite loops
            
            while page <= max_pages:
                # Construct URL with page number
                if hasattr(self, 'category_path'):
                    url = f"{self.base_domain}/{self.category_path}/{page}"
                else:
                    # Fallback to original URL with page number
                    url = f"{self.base_url.rstrip('/1234567890')}/{page}"
                
                print(f"  Scraping page {page}...")
                page_jobs = self._scrape_page(url, filter_today_only)
                
                if not page_jobs:
                    # No jobs found, stop pagination
                    break
                
                # Filter for today's jobs if needed
                if filter_today_only:
                    today = datetime.now().date()
                    today_jobs = []
                    for job in page_jobs:
                        job_date = job.get('date_posted')
                        if job_date:
                            if isinstance(job_date, datetime):
                                job_date = job_date.date()
                            elif isinstance(job_date, str):
                                parsed_date = self.parse_date(job_date)
                                if parsed_date:
                                    job_date = parsed_date.date()
                                else:
                                    continue
                            
                            if job_date == today:
                                today_jobs.append(job)
                            else:
                                # Found non-today job - stop (jobs are sorted newest to oldest)
                                print(f"  Found job posted on {job_date} - stopping (jobs are sorted newest to oldest)")
                                jobs.extend(today_jobs)
                                return jobs
                        else:
                            # No date, skip it
                            continue
                    
                    jobs.extend(today_jobs)
                    if not today_jobs:
                        # No today jobs on this page, stop
                        break
                else:
                    jobs.extend(page_jobs)
                
                # Check if there are more pages
                if len(page_jobs) < 15:  # Assuming ~15 jobs per page
                    break
                
                page += 1
            
            if filter_today_only:
                print(f"  Found {len(jobs)} job(s) posted today")
            else:
                print(f"  Found {len(jobs)} total jobs")
            
        except Exception as e:
            print(f"  Error scraping Synopsys jobs: {e}")
            import traceback
            traceback.print_exc()
        
        return jobs
    
    def _scrape_page(self, url, filter_today_only=True):
        """Scrape a single page of jobs"""
        jobs = []
        
        try:
            response = self.fetch_page(url)
            if not response:
                return jobs
            
            soup = BeautifulSoup(response.content, 'lxml')
            
            # Find job listings
            job_elements = self._find_job_elements(soup)
            
            for element in job_elements:
                job = self._parse_job_element(element)
                if job:
                    jobs.append(job)
        
        except Exception as e:
            print(f"  Error scraping page {url}: {e}")
        
        return jobs
    
    def _find_job_elements(self, soup):
        """Find job listing elements in HTML"""
        # Synopsys jobs are in <li class="search-results-list__list-item">
        job_elements = soup.find_all('li', class_='search-results-list__list-item')
        return job_elements
    
    def _parse_job_element(self, element):
        """Parse a single job element from HTML"""
        try:
            # Find the job link
            job_link = element.find('a', class_='sr-job-link')
            if not job_link:
                return None
            
            # Extract title from <h2> inside the link
            title_elem = job_link.find('h2')
            if not title_elem:
                return None
            
            title = title_elem.get_text(strip=True)
            # Remove the arrow image text if present
            title = re.sub(r'\s*circle arrow\s*$', '', title, flags=re.I).strip()
            if not title or len(title) < 5:
                return None
            
            # Extract URL
            url = job_link.get('href', '')
            if url and not url.startswith('http'):
                url = urljoin(self.base_domain, url)
            
            # Extract Job ID from <span class="jobId"> (this is the short ID shown on the page)
            job_id = None
            job_id_elem = element.find('span', class_='jobId')
            if job_id_elem:
                job_id_match = re.search(r'Job ID:\s*(\d+)', job_id_elem.get_text(), re.I)
                if job_id_match:
                    job_id = job_id_match.group(1)
            
            # Fallback to data-job-id from link or URL
            if not job_id:
                job_id = job_link.get('data-job-id')
                if not job_id:
                    # Try to extract from URL: /job/.../44408/89812463552
                    url_match = re.search(r'/(\d+)/?$', url)
                    if url_match:
                        job_id = url_match.group(1)
            
            if not job_id:
                return None
            
            # Extract location from <span class="job-location">
            location = 'N/A'
            location_elem = element.find('span', class_='job-location')
            if location_elem:
                location_text = location_elem.get_text(strip=True)
                # Remove the pin icon text if present
                location = re.sub(r'^(pin icon|map icon)\s*', '', location_text, flags=re.I).strip()
            
            # Extract Posted Date from <span class="job-date-posted">
            date_posted = None
            date_elem = element.find('span', class_='job-date-posted')
            if date_elem:
                date_text = date_elem.get_text(strip=True)
                # Extract date: "Posted: 12/22/2025"
                date_match = re.search(r'Posted:\s*(\d{1,2}/\d{1,2}/\d{4})', date_text, re.I)
                if date_match:
                    date_str = date_match.group(1)
                    # Parse MM/DD/YYYY format
                    try:
                        date_posted = datetime.strptime(date_str, '%m/%d/%Y')
                    except:
                        date_posted = self.parse_date(date_str)
            
            return {
                'job_id': f"synopsys_{job_id}",
                'title': title,
                'location': location,
                'description': '',
                'date_posted': date_posted,
                'source': self.source_name,
                'url': url or self.base_url
            }
            
        except Exception as e:
            print(f"  Error parsing job element: {e}")
            return None

