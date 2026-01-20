"""
Texas Instruments Careers scraper
Scrapes job listings from Texas Instruments' career page
Handles infinite scroll to get all jobs
"""
import re
import time
from bs4 import BeautifulSoup
from .base_scraper import BaseScraper
from datetime import datetime
from urllib.parse import urlparse, urljoin

try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException, NoSuchElementException
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False


class TIScraper(BaseScraper):
    """
    Scraper for Texas Instruments careers page
    Handles infinite scroll to get all jobs from HTML
    """
    
    def __init__(self, base_url):
        super().__init__("ti", base_url)
        parsed_url = urlparse(base_url)
        self.base_domain = f"{parsed_url.scheme}://{parsed_url.netloc}"
        
        # Extract site code from URL (e.g., "CX" from /en/sites/CX/jobs)
        path_parts = parsed_url.path.strip('/').split('/')
        if 'sites' in path_parts:
            site_idx = path_parts.index('sites')
            if site_idx + 1 < len(path_parts):
                self.site_code = path_parts[site_idx + 1]
            else:
                self.site_code = 'CX'  # Default
        else:
            self.site_code = 'CX'
    
    def scrape_jobs(self, filter_today_only=False, **kwargs):
        """
        Scrape jobs from Texas Instruments career page
        Handles infinite scroll to get all jobs
        
        Args:
            filter_today_only: If True, only return jobs posted today
                              Note: Database handles duplicates, so this is mainly for testing
        
        Returns:
            list: List of job dictionaries
        """
        jobs = []
        
        try:
            if SELENIUM_AVAILABLE:
                # Use Selenium to handle infinite scroll
                jobs = self._scrape_with_selenium(filter_today_only)
            else:
                # Fallback to basic HTML scraping (may not get all jobs due to infinite scroll)
                print("  Warning: Selenium not available. Install selenium to handle infinite scroll.")
                print("  Falling back to basic HTML scraping (may miss jobs loaded via scroll)")
                jobs = self._scrape_basic_html(filter_today_only)
        except Exception as e:
            print(f"  Error scraping TI jobs: {e}")
            import traceback
            traceback.print_exc()
        
        return jobs
    
    def _scrape_with_selenium(self, filter_today_only=False, db=None):
        """Scrape jobs using Selenium to handle infinite scroll"""
        jobs = []
        driver = None
        
        try:
            print("  Using Selenium to handle infinite scroll...")
            
            # Setup Chrome options
            from selenium.webdriver.chrome.options import Options
            chrome_options = Options()
            chrome_options.add_argument('--headless')  # Run in background
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument(f'user-agent={self.session.headers["User-Agent"]}')
            
            # Create driver
            driver = webdriver.Chrome(options=chrome_options)
            driver.set_page_load_timeout(30)
            
            # Load the page
            print(f"  Loading page: {self.base_url}")
            driver.get(self.base_url)
            
            # Wait for job list to load
            wait = WebDriverWait(driver, 10)
            try:
                wait.until(EC.presence_of_element_located((By.CLASS_NAME, "job-list-item__link")))
            except TimeoutException:
                print("  Warning: Job list not found, trying to continue anyway...")
            
            # Scroll incrementally and check for duplicates as we go
            print("  Scrolling and checking for new jobs...")
            last_height = driver.execute_script("return document.body.scrollHeight")
            scroll_attempts = 0
            max_scroll_attempts = 50  # Safety limit
            found_duplicate = False
            
            while scroll_attempts < max_scroll_attempts and not found_duplicate:
                # Scroll to bottom
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                
                # Wait for new content to load
                time.sleep(2)
                
                # Check if new content loaded
                new_height = driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    # No new content, we've reached the end
                    print(f"  Reached end of scroll after {scroll_attempts} attempts")
                    break
                
                last_height = new_height
                scroll_attempts += 1
                
                # Check current job links for duplicates (if db provided)
                if db and scroll_attempts % 3 == 0:  # Check every 3 scrolls to avoid too many checks
                    job_links = driver.find_elements(By.CLASS_NAME, "job-list-item__link")
                    # Check the most recent jobs first (they appear first in the list)
                    for link in job_links[:10]:  # Check first 10 links
                        href = link.get_attribute('href')
                        if href:
                            job_id = self._extract_job_id_from_url(href)
                            if job_id and db.job_exists(f"ti_{job_id}"):
                                print(f"  Found duplicate job (ID: {job_id}) - stopping early")
                                found_duplicate = True
                                break
                    if found_duplicate:
                        break
                
                # Show progress every 5 scrolls
                if scroll_attempts % 5 == 0:
                    job_links = driver.find_elements(By.CLASS_NAME, "job-list-item__link")
                    print(f"  Scrolled {scroll_attempts} times, found {len(job_links)} job links so far...")
            
            # Get all job links
            job_links = driver.find_elements(By.CLASS_NAME, "job-list-item__link")
            print(f"  Found {len(job_links)} total job links")
            
            # Extract job URLs and check for duplicates
            job_urls = []
            seen_urls = set()
            for link in job_links:
                href = link.get_attribute('href')
                if href and href not in seen_urls:
                    seen_urls.add(href)
                    job_urls.append(href)
            
            print(f"  Processing {len(job_urls)} unique jobs...")
            
            # Extract job details from each job page, stopping at first duplicate
            for i, job_url in enumerate(job_urls, 1):
                # Extract job ID from URL first to check database early
                job_id = self._extract_job_id_from_url(job_url)
                
                # Check database if provided
                if db and job_id:
                    if db.job_exists(f"ti_{job_id}"):
                        print(f"  Found duplicate job (ID: {job_id}) at position {i} - stopping")
                        print(f"  Processed {i-1} new jobs before finding duplicate")
                        break
                
                if i % 10 == 0:
                    print(f"  Processing job {i}/{len(job_urls)}...")
                
                job = self._extract_job_details(job_url, driver)
                if job:
                    if filter_today_only:
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
                            
                            today = datetime.now().date()
                            if job_date == today:
                                jobs.append(job)
                            else:
                                # Jobs are sorted newest to oldest, stop here
                                print(f"  Found job posted on {job_date} - stopping")
                                break
                        else:
                            continue
                    else:
                        jobs.append(job)
            
            print(f"  Extracted {len(jobs)} new jobs")
            
        except Exception as e:
            print(f"  Error scraping with Selenium: {e}")
            import traceback
            traceback.print_exc()
        finally:
            if driver:
                driver.quit()
        
        return jobs
    
    def _scrape_basic_html(self, filter_today_only=False, db=None):
        """Basic HTML scraping without Selenium (may miss jobs due to infinite scroll)"""
        jobs = []
        
        try:
            print("  Scraping HTML (without infinite scroll support)...")
            response = self.fetch_page(self.base_url)
            
            if not response:
                return jobs
            
            soup = BeautifulSoup(response.content, 'lxml')
            
            # Find all job links
            job_links = soup.find_all('a', class_='job-list-item__link')
            print(f"  Found {len(job_links)} job links in initial HTML")
            
            # Extract job URLs
            job_urls = []
            seen_urls = set()
            for link in job_links:
                href = link.get('href')
                if href:
                    if not href.startswith('http'):
                        href = urljoin(self.base_domain, href)
                    if href not in seen_urls:
                        seen_urls.add(href)
                        job_urls.append(href)
            
            print(f"  Processing {len(job_urls)} unique jobs...")
            
            # Extract job details from each job page, stopping at first duplicate
            for i, job_url in enumerate(job_urls, 1):
                # Extract job ID from URL first to check database early
                job_id = self._extract_job_id_from_url(job_url)
                
                # Check database if provided
                if db and job_id:
                    if db.job_exists(f"ti_{job_id}"):
                        print(f"  Found duplicate job (ID: {job_id}) at position {i} - stopping")
                        print(f"  Processed {i-1} new jobs before finding duplicate")
                        break
                
                if i % 10 == 0:
                    print(f"  Processing job {i}/{len(job_urls)}...")
                
                job = self._extract_job_details_from_url(job_url)
                if job:
                    if filter_today_only:
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
                            
                            today = datetime.now().date()
                            if job_date == today:
                                jobs.append(job)
                            else:
                                # Jobs are sorted newest to oldest, stop here
                                print(f"  Found job posted on {job_date} - stopping")
                                break
                        else:
                            continue
                    else:
                        jobs.append(job)
            
            print(f"  Extracted {len(jobs)} new jobs")
            
        except Exception as e:
            print(f"  Error scraping HTML: {e}")
            import traceback
            traceback.print_exc()
        
        return jobs
    
    def _extract_job_details(self, job_url, driver=None):
        """Extract job details from a job URL using Selenium"""
        try:
            if driver:
                # Use existing driver to navigate
                driver.get(job_url)
                time.sleep(1)  # Wait for page to load
                page_source = driver.page_source
            else:
                # Fetch page normally
                response = self.fetch_page(job_url)
                if not response:
                    return None
                page_source = response.text
            
            soup = BeautifulSoup(page_source, 'lxml')
            return self._parse_job_page(soup, job_url)
        
        except Exception as e:
            print(f"    Error extracting job details from {job_url}: {e}")
            return None
    
    def _extract_job_details_from_url(self, job_url):
        """Extract job details from a job URL"""
        return self._extract_job_details(job_url, driver=None)
    
    def _extract_job_id_from_url(self, job_url):
        """Extract job ID from URL without parsing the full page"""
        # URL format: https://careers.ti.com/en/sites/CX/job/25000232/?sortBy=POSTING_DATES_DESC
        job_id_match = re.search(r'/job/(\d+)', job_url)
        return job_id_match.group(1) if job_id_match else None
    
    def _parse_job_page(self, soup, job_url):
        """Parse job details from a job page HTML"""
        try:
            # Extract job ID from URL
            job_id = self._extract_job_id_from_url(job_url)
            
            if not job_id:
                # Try to extract from page
                job_id_elem = soup.find(attrs={'data-job-id': True}) or soup.find('div', id=re.compile(r'job|requisition', re.I))
                if job_id_elem:
                    job_id = job_id_elem.get('data-job-id') or job_id_elem.get('id')
            
            if not job_id:
                # Use hash of URL as fallback
                job_id = str(abs(hash(job_url)))
            
            # Extract title
            title = None
            title_selectors = [
                soup.find('h1'),
                soup.find('h2', class_=re.compile(r'title|job', re.I)),
                soup.find('div', class_=re.compile(r'job-title|position-title', re.I)),
                soup.find('span', class_=re.compile(r'title|job-title', re.I)),
            ]
            
            for selector in title_selectors:
                if selector:
                    title = selector.get_text(strip=True)
                    if title and len(title) > 5:
                        break
            
            if not title:
                return None
            
            # Extract location
            location = 'N/A'
            location_selectors = [
                soup.find('div', class_=re.compile(r'location', re.I)),
                soup.find('span', class_=re.compile(r'location', re.I)),
                soup.find('li', class_=re.compile(r'location', re.I)),
                soup.find(string=re.compile(r'United States|Canada|Texas|California|Dallas|Austin', re.I)),
            ]
            
            for selector in location_selectors:
                if selector:
                    if hasattr(selector, 'get_text'):
                        location = selector.get_text(strip=True)
                    elif isinstance(selector, str):
                        location = selector.strip()
                    else:
                        location = str(selector).strip()
                    if location and location != 'N/A':
                        break
            
            # Extract date posted
            date_posted = None
            date_selectors = [
                soup.find('time'),
                soup.find('div', class_=re.compile(r'date|posted', re.I)),
                soup.find('span', class_=re.compile(r'date|posted', re.I)),
                soup.find(string=re.compile(r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}-\d{2}-\d{2}', re.I)),
            ]
            
            for selector in date_selectors:
                if selector:
                    date_str = ''
                    if selector.name == 'time' and selector.get('datetime'):
                        date_str = selector['datetime']
                    elif hasattr(selector, 'get_text'):
                        date_str = selector.get_text(strip=True)
                    elif isinstance(selector, str):
                        date_str = selector.strip()
                    else:
                        date_str = str(selector).strip()
                    
                    if date_str:
                        date_posted = self.parse_date(date_str)
                        if date_posted:
                            break
            
            # Extract description
            description = ''
            desc_selectors = [
                soup.find('div', class_=re.compile(r'description|summary|job-description', re.I)),
                soup.find('section', class_=re.compile(r'description|summary', re.I)),
                soup.find('div', id=re.compile(r'description|summary', re.I)),
            ]
            
            for selector in desc_selectors:
                if selector:
                    description = selector.get_text(strip=True)
                    if description and len(description) > 50:
                        break
            
            return {
                'job_id': f"ti_{job_id}",
                'title': title,
                'location': location,
                'description': description,
                'date_posted': date_posted or datetime.now(),
                'source': self.source_name,
                'url': job_url
            }
        
        except Exception as e:
            print(f"    Error parsing job page: {e}")
            return None
