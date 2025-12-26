"""
Google Careers scraper
Scrapes job listings from Google careers page
Extracts data from embedded JavaScript (AF_initDataCallback)
"""
import json
import re
from bs4 import BeautifulSoup
from .base_scraper import BaseScraper
from datetime import datetime
from urllib.parse import urlparse, urljoin, parse_qs


class GoogleScraper(BaseScraper):
    """
    Scraper for Google careers page
    Extracts job data from embedded JavaScript
    """
    
    def __init__(self, base_url):
        super().__init__("google", base_url)
        # Extract base URL
        parsed_url = urlparse(base_url)
        self.base_domain = f"{parsed_url.scheme}://{parsed_url.netloc}"
        
        # Parse query parameters
        query_params = parse_qs(parsed_url.query)
        self.locations = query_params.get('location', [])
        self.target_levels = query_params.get('target_level', [])
        self.employment_type = query_params.get('employment_type', [])
        self.sort_by = query_params.get('sort_by', ['date'])[0]
    
    def scrape_jobs(self, filter_today_only=False, **kwargs):
        """
        Scrape jobs from Google career page with pagination
        
        Args:
            filter_today_only: Ignored (no dates available in embedded data)
        
        Returns:
            list: List of job dictionaries
        """
        jobs = []
        
        try:
            page = 1
            max_pages = 100  # Safety limit to prevent infinite loops
            
            while page <= max_pages:
                # Construct URL with page parameter
                if page == 1:
                    url = self.base_url
                else:
                    # Add page parameter
                    separator = '&' if '?' in self.base_url else '?'
                    url = f"{self.base_url}{separator}page={page}"
                
                print(f"  Scraping page {page}...")
                response = self.fetch_page(url)
                if not response:
                    break
                
                soup = BeautifulSoup(response.content, 'lxml')
                
                # Extract jobs from this page
                page_jobs = self._extract_jobs_from_scripts(soup)
                
                if not page_jobs:
                    # No more jobs, stop pagination
                    print(f"  No jobs found on page {page}, stopping pagination")
                    break
                
                jobs.extend(page_jobs)
                print(f"  Found {len(page_jobs)} jobs on page {page} (total so far: {len(jobs)})")
                
                # If we got fewer than 20 jobs, we're probably on the last page
                if len(page_jobs) < 20:
                    print(f"  Last page reached (got {len(page_jobs)} jobs, expected 20)")
                    break
                
                page += 1
            
            print(f"  Found {len(jobs)} total jobs across {page - 1} page(s)")
            
        except Exception as e:
            print(f"  Error scraping Google jobs: {e}")
            import traceback
            traceback.print_exc()
        
        return jobs
    
    def _extract_jobs_from_scripts(self, soup):
        """Extract job data from embedded JavaScript (AF_initDataCallback)"""
        jobs = []
        job_data_map = {}  # Map job_id to job data from JavaScript
        
        try:
            # Find all script tags
            scripts = soup.find_all('script')
            
            for script in scripts:
                if not script.string:
                    continue
                
                script_text = script.string
                
                # Look for AF_initDataCallback pattern
                # Format: AF_initDataCallback({key: 'ds:1', hash: '2', data:[[[...]]]})
                if 'AF_initDataCallback' in script_text and 'ds:1' in script_text:
                    # Extract job data from the callback
                    # Pattern: [["job_id", "title", "url", [description], [location], ...]]
                    # Jobs are in nested arrays
                    job_pattern = r'\["(\d+)","([^"]+)","([^"]+)"'
                    matches = re.finditer(job_pattern, script_text)
                    
                    for match in matches:
                        try:
                            job_id = match.group(1)
                            title = match.group(2)
                            url = match.group(3)
                            
                            # Clean up URL (may have unicode escapes)
                            url = url.replace('\\u003d', '=').replace('\\u0026', '&').replace('\\u002F', '/')
                            
                            # Skip if it's not a valid job URL
                            if 'signin' not in url and 'careers' not in url.lower():
                                continue
                            
                            # Extract location from URL (more reliable)
                            location = 'N/A'
                            if 'loc=US' in url:
                                location = 'United States'
                            elif 'loc=CA' in url:
                                location = 'Canada'
                            else:
                                # Try to find location in nearby script text
                                match_end = match.end()
                                nearby_text = script_text[match_end:match_end+1000]
                                location_match = re.search(r'\["([^"]+)"(?:,"([^"]+)")?\]', nearby_text)
                                if location_match:
                                    location = location_match.group(1)
                            
                            # Build full URL
                            if not url.startswith('http'):
                                if url.startswith('/'):
                                    url = urljoin(self.base_domain, url)
                                else:
                                    url = f"{self.base_domain}/about/careers/applications/{url}"
                            
                            job_data_map[job_id] = {
                                'job_id': f"google_{job_id}",
                                'title': title,
                                'location': location,
                                'url': url
                            }
                            
                        except Exception as e:
                            continue
            
            # Now extract from HTML to get more complete data
            html_jobs = self._extract_jobs_from_html(soup)
            
            # Merge data from JavaScript and HTML
            for html_job in html_jobs:
                # Extract numeric job ID from google_job_id
                job_id_match = re.search(r'google_(\d+)', html_job.get('job_id', ''))
                if job_id_match:
                    numeric_id = job_id_match.group(1)
                    if numeric_id in job_data_map:
                        # Use data from JavaScript (more complete)
                        job = job_data_map[numeric_id].copy()
                        job['description'] = html_job.get('description', '')
                        job['date_posted'] = None
                        job['source'] = self.source_name
                        jobs.append(job)
                    else:
                        # Use HTML data
                        jobs.append(html_job)
                else:
                    jobs.append(html_job)
            
            # If we have JavaScript data but no HTML matches, use JavaScript data
            if not jobs and job_data_map:
                for job_id, job_data in job_data_map.items():
                    job = job_data.copy()
                    job['description'] = ''
                    job['date_posted'] = None
                    job['source'] = self.source_name
                    jobs.append(job)
            
        except Exception as e:
            print(f"  Error extracting jobs from scripts: {e}")
            import traceback
            traceback.print_exc()
        
        return jobs
    
    def _extract_jobs_from_html(self, soup):
        """Extract jobs from HTML structure"""
        jobs = []
        
        try:
            # Google renders jobs in <li> elements with ssk attribute containing job ID
            # Format: <li class="lLd3Je" ssk="17:74163612683248326">
            job_list_items = soup.find_all('li', attrs={'ssk': True})
            
            for item in job_list_items:
                try:
                    # Extract job ID from ssk attribute (format: "17:74163612683248326")
                    ssk = item.get('ssk', '')
                    job_id_match = re.search(r':(\d+)', ssk)
                    if not job_id_match:
                        continue
                    
                    job_id = job_id_match.group(1)
                    
                    # Find title in h3 tag
                    title_elem = item.find('h3')
                    if not title_elem:
                        continue
                    
                    title = title_elem.get_text(strip=True)
                    if not title or len(title) < 5:
                        continue
                    
                    # Find location - extract from URL parameters in links
                    location = 'N/A'
                    links = item.find_all('a', href=True)
                    for link in links:
                        href = link.get('href', '')
                        if 'loc=' in href:
                            loc_match = re.search(r'loc=([A-Z]{2})', href)
                            if loc_match:
                                loc_code = loc_match.group(1)
                                location = 'United States' if loc_code == 'US' else 'Canada' if loc_code == 'CA' else loc_code
                                break
                    
                    # Fallback: Look for location in class names or text
                    if location == 'N/A':
                        location_elem = item.find(class_=re.compile(r'location', re.I))
                        if location_elem:
                            location = location_elem.get_text(strip=True)
                        else:
                            # Check text content
                            location_text = item.get_text()
                            if 'United States' in location_text:
                                location = 'United States'
                            elif 'Canada' in location_text:
                                location = 'Canada'
                    
                    # Find URL - look for link with href containing job ID
                    link = item.find('a', href=re.compile(r'jobs/results|jobId', re.I))
                    if not link:
                        # Construct URL from job ID and title
                        title_slug = re.sub(r'[^a-z0-9]+', '-', title.lower())
                        url = f"{self.base_domain}/about/careers/applications/jobs/results/{job_id}-{title_slug}"
                    else:
                        href = link.get('href', '')
                        url = href if href.startswith('http') else urljoin(self.base_domain, href)
                    
                    # Extract description if available
                    description = ''
                    desc_elem = item.find(class_=re.compile(r'description|summary', re.I))
                    if desc_elem:
                        description = desc_elem.get_text(strip=True)
                    
                    job = {
                        'job_id': f"google_{job_id}",
                        'title': title,
                        'location': location,
                        'description': description,
                        'date_posted': None,  # Google doesn't provide dates in HTML
                        'source': self.source_name,
                        'url': url
                    }
                    
                    jobs.append(job)
                    
                except Exception as e:
                    continue
            
            # If no jobs found with ssk, try finding links
            if not jobs:
                job_links = soup.find_all('a', href=re.compile(r'jobs/results/\d+', re.I))
                
                for link in job_links:
                    try:
                        href = link.get('href', '')
                        title = link.get_text(strip=True) or link.get('aria-label', '')
                        
                        if not title or len(title) < 5:
                            continue
                        
                        # Extract job ID from URL (format: jobs/results/74163612683248326-...)
                        job_id_match = re.search(r'jobs/results/(\d+)', href)
                        if not job_id_match:
                            continue
                        
                        job_id = job_id_match.group(1)
                        
                        url = href if href.startswith('http') else urljoin(self.base_domain, href)
                        
                        job = {
                            'job_id': f"google_{job_id}",
                            'title': title,
                            'location': 'N/A',
                            'description': '',
                            'date_posted': None,
                            'source': self.source_name,
                            'url': url
                        }
                        
                        jobs.append(job)
                    except:
                        continue
        
        except Exception as e:
            print(f"  Error extracting jobs from HTML: {e}")
        
        return jobs

