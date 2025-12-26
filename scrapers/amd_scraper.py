"""
AMD Careers scraper
Scrapes job listings from AMD's career page
"""
import json
import re
from bs4 import BeautifulSoup
from .base_scraper import BaseScraper
from datetime import datetime
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse


class AMDScraper(BaseScraper):
    """
    Scraper for AMD careers page
    Supports filtering by country (United States, Canada)
    Jobs are sorted by posted_date descending
    """
    
    def __init__(self, base_url):
        super().__init__("amd", base_url)
        # Extract base URL and parameters
        parsed_url = urlparse(base_url)
        self.base_domain = f"{parsed_url.scheme}://{parsed_url.netloc}"
        self.base_path = parsed_url.path
        
        # AMD uses Jibe ATS - try to find API endpoint
        # Jibe typically uses /api/search or /api/jobs endpoints
        self.api_endpoint = f"{self.base_domain}/api/search"
        
        # Parse query parameters
        query_params = parse_qs(parsed_url.query)
        self.countries = query_params.get('country', [])
        self.sort_by = query_params.get('sortBy', ['posted_date'])[0]
        self.descending = query_params.get('descending', ['true'])[0] == 'true'
    
    def scrape_jobs(self, filter_today_only=True, **kwargs):
        """
        Scrape jobs from AMD career page
        
        Args:
            filter_today_only: If True, only return jobs posted today
                              Since jobs are sorted by date descending, stops at first non-today job
        
        Returns:
            list: List of job dictionaries
        """
        jobs = []
        
        try:
            # Try API first (Jibe platform)
            api_jobs = self._scrape_via_api(filter_today_only)
            if api_jobs:
                jobs.extend(api_jobs)
                return jobs
            
            # Fallback to HTML scraping
            page = 1
            found_non_today_job = False
            
            while not found_non_today_job:
                page_jobs = self._scrape_page(page)
                
                if not page_jobs:
                    # No more jobs
                    break
                
                for job in page_jobs:
                    # Check date if filtering for today only
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
                                    # Can't parse date, skip it
                                    continue
                            
                            today = datetime.now().date()
                            if job_date == today:
                                jobs.append(job)
                            else:
                                # Found a job not posted today - stop (jobs are sorted newest to oldest)
                                found_non_today_job = True
                                print(f"  Found job posted on {job_date} - stopping (jobs are sorted newest to oldest)")
                                break
                        else:
                            # No date, skip it
                            continue
                    else:
                        # Not filtering, add all jobs
                        jobs.append(job)
                
                # If we found a non-today job or got fewer jobs than expected, stop pagination
                if found_non_today_job or len(page_jobs) == 0:
                    break
                
                page += 1
            
            if filter_today_only:
                print(f"  Found {len(jobs)} job(s) posted today")
            else:
                print(f"  Found {len(jobs)} total jobs")
            
        except Exception as e:
            print(f"  Error scraping AMD jobs: {e}")
            import traceback
            traceback.print_exc()
        
        return jobs
    
    def _scrape_via_api(self, filter_today_only=True):
        """Try to scrape using Jibe API"""
        jobs = []
        
        try:
            # Jibe API typically uses POST requests with search parameters
            # Try different API endpoint patterns
            api_endpoints = [
                f"{self.base_domain}/api/search",
                f"{self.base_domain}/api/jobs",
                f"{self.base_domain}/careers-home/api/search",
            ]
            
            # Build query parameters from URL
            parsed_url = urlparse(self.base_url)
            query_params = parse_qs(parsed_url.query)
            
            # Prepare API request payload
            # Jibe typically expects parameters like: country, page, sortBy, descending
            payload = {
                'country': query_params.get('country', ['United States|Canada'])[0],
                'page': query_params.get('page', ['1'])[0],
                'sortBy': query_params.get('sortBy', ['posted_date'])[0],
                'descending': query_params.get('descending', ['true'])[0],
            }
            
            headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'User-Agent': self.session.headers['User-Agent']
            }
            
            for api_url in api_endpoints:
                print(f"  Trying API endpoint: {api_url}")
                
                # Try POST first (most common for Jibe)
                response = self.session.post(api_url, json=payload, headers=headers, timeout=30)
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        # Jibe might return jobs in different structures
                        job_list = (
                            data.get('jobs') or
                            data.get('positions') or
                            data.get('results') or
                            data.get('data', {}).get('jobs') or
                            []
                        )
                        
                        if job_list:
                            print(f"  Found {len(job_list)} jobs via API")
                            today = datetime.now().date()
                            
                            for job_item in job_list:
                                # Jibe API wraps jobs in a 'data' object
                                job_data = job_item.get('data', job_item)
                                job = self._parse_api_job(job_data)
                                if job:
                                    # Check date if filtering
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
                                                    # Can't parse date, skip it
                                                    continue
                                            
                                            if job_date == today:
                                                jobs.append(job)
                                            else:
                                                # Found non-today job - stop (jobs are sorted newest to oldest)
                                                print(f"  Found job posted on {job_date} - stopping (jobs are sorted newest to oldest)")
                                                return jobs
                                        else:
                                            # No date, skip it
                                            continue
                                    else:
                                        jobs.append(job)
                            
                            if jobs or not filter_today_only:
                                return jobs
                    except json.JSONDecodeError:
                        continue
                
                # Try GET request
                response = self.session.get(api_url, params=payload, headers=headers, timeout=30)
                if response.status_code == 200:
                    try:
                        data = response.json()
                        job_list = (
                            data.get('jobs') or
                            data.get('positions') or
                            data.get('results') or
                            []
                        )
                        if job_list:
                            print(f"  Found {len(job_list)} jobs via API (GET)")
                            today = datetime.now().date()
                            
                            for job_item in job_list:
                                # Jibe API wraps jobs in a 'data' object
                                job_data = job_item.get('data', job_item)
                                job = self._parse_api_job(job_data)
                                if job:
                                    # Check date if filtering
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
                                                    # Can't parse date, skip it
                                                    continue
                                            
                                            if job_date == today:
                                                jobs.append(job)
                                            else:
                                                # Found non-today job - stop (jobs are sorted newest to oldest)
                                                print(f"  Found job posted on {job_date} - stopping (jobs are sorted newest to oldest)")
                                                return jobs
                                        else:
                                            # No date, skip it
                                            continue
                                    else:
                                        jobs.append(job)
                            
                            if jobs or not filter_today_only:
                                return jobs
                    except json.JSONDecodeError:
                        continue
        
        except Exception as e:
            print(f"  API scrape failed: {e}")
        
        return jobs
    
    def _parse_api_job(self, job_data):
        """Parse a job from Jibe API response"""
        try:
            # Jibe API structure - jobs are in data object with these fields:
            # slug, req_id, title, location_name, posted_date, apply_url, description
            job_id = (
                str(job_data.get('req_id')) or
                str(job_data.get('slug')) or
                str(job_data.get('id')) or
                ''
            )
            
            title = job_data.get('title', '')
            
            if not title or not job_id:
                return None
            
            # Location - try multiple fields
            location = (
                job_data.get('full_location') or
                job_data.get('short_location') or
                job_data.get('location_name') or
                job_data.get('city') or
                'N/A'
            )
            
            # Parse date - Jibe uses ISO format: "2025-12-20T05:08:00+0000"
            date_posted = None
            date_str = job_data.get('posted_date') or job_data.get('postedDate') or ''
            
            if date_str:
                # Try parsing ISO format first
                try:
                    # Handle ISO format with timezone: "2025-12-20T05:08:00+0000"
                    if 'T' in date_str:
                        # Extract date part (before T)
                        date_part = date_str.split('T')[0]
                        # Parse as date only (YYYY-MM-DD)
                        date_posted = datetime.strptime(date_part, '%Y-%m-%d')
                    else:
                        date_posted = self.parse_date(date_str)
                except Exception as e:
                    # Fallback to parse_date method
                    date_posted = self.parse_date(date_str)
            
            # Get URL - Jibe provides apply_url
            url = (
                job_data.get('apply_url') or
                job_data.get('canonical_url') or
                job_data.get('url') or
                ''
            )
            
            if url and not url.startswith('http'):
                url = f"{self.base_domain}{url}"
            elif not url:
                # Construct URL from slug/req_id
                slug = job_data.get('slug') or job_id
                url = f"{self.base_domain}/jobs/{slug}"
            
            description = job_data.get('description') or ''
            
            return {
                'job_id': f"amd_{job_id}",
                'title': title,
                'location': location,
                'description': description,
                'date_posted': date_posted or datetime.now(),
                'source': self.source_name,
                'url': url or self.base_url
            }
            
        except Exception as e:
            print(f"  Error parsing API job: {e}")
            return None
    
    def _scrape_page(self, page_num):
        """Scrape a single page of jobs"""
        jobs = []
        
        try:
            # Build URL with page number
            parsed_url = urlparse(self.base_url)
            query_params = parse_qs(parsed_url.query)
            query_params['page'] = [str(page_num)]
            
            # Rebuild URL
            new_query = urlencode(query_params, doseq=True)
            url = urlunparse((
                parsed_url.scheme,
                parsed_url.netloc,
                parsed_url.path,
                parsed_url.params,
                new_query,
                parsed_url.fragment
            ))
            
            print(f"  Scraping page {page_num}...")
            response = self.fetch_page(url)
            
            if not response:
                return jobs
            
            soup = BeautifulSoup(response.content, 'lxml')
            
            # Try to find job listings - AMD likely uses specific classes or data attributes
            # Look for common patterns
            job_elements = self._find_job_elements(soup)
            
            if not job_elements:
                # Try to find JSON data embedded in the page
                jobs = self._scrape_embedded_json(soup)
                if jobs:
                    return jobs
                return jobs
            
            # Parse each job element
            for element in job_elements:
                job = self._parse_job_element(element)
                if job:
                    jobs.append(job)
            
        except Exception as e:
            print(f"  Error scraping page {page_num}: {e}")
        
        return jobs
    
    def _find_job_elements(self, soup):
        """Find job listing elements in the HTML"""
        # Try multiple selectors - AMD might use various patterns
        selectors = [
            # Common job listing patterns
            soup.find_all('div', class_=re.compile(r'job|listing|card|item', re.I)),
            soup.find_all('li', class_=re.compile(r'job|listing|card|item', re.I)),
            soup.find_all('article', class_=re.compile(r'job|listing|card|item', re.I)),
            soup.find_all('a', href=re.compile(r'/job|/careers|/position', re.I)),
            # Data attributes
            soup.find_all(attrs={'data-job-id': True}),
            soup.find_all(attrs={'data-automation-id': re.compile(r'job', re.I)}),
        ]
        
        for selector_result in selectors:
            if selector_result:
                # Filter to only actual job listings (have title or link)
                filtered = [
                    elem for elem in selector_result
                    if elem.find('a', href=re.compile(r'/job|/careers', re.I)) or
                       elem.find(string=re.compile(r'engineer|developer|software|hardware', re.I))
                ]
                if filtered:
                    return filtered
        
        return []
    
    def _parse_job_element(self, element):
        """Parse a single job element"""
        try:
            # Find title
            title_elem = (
                element.find('h2') or
                element.find('h3') or
                element.find('h4') or
                element.find('a', class_=re.compile(r'title|job', re.I)) or
                element.find('span', class_=re.compile(r'title|job', re.I))
            )
            
            if not title_elem:
                # Try to find any link that might be the job title
                link = element.find('a', href=re.compile(r'/job|/careers', re.I))
                if link:
                    title_elem = link
            
            if not title_elem:
                return None
            
            title = title_elem.get_text(strip=True) if hasattr(title_elem, 'get_text') else str(title_elem).strip()
            if not title or len(title) < 5:
                return None
            
            # Find URL
            url = None
            link = element.find('a', href=True)
            if link:
                url = link['href']
                if not url.startswith('http'):
                    url = f"{self.base_domain}{url}"
            elif title_elem and title_elem.name == 'a' and title_elem.get('href'):
                url = title_elem['href']
                if not url.startswith('http'):
                    url = f"{self.base_domain}{url}"
            
            # Extract job ID from URL
            job_id = None
            if url:
                # Try to extract ID from URL (e.g., /job/12345 or /careers/job/12345)
                match = re.search(r'/(\d+)/?$', url) or re.search(r'job[_-]?(\d+)', url, re.I)
                if match:
                    job_id = match.group(1)
                else:
                    # Use hash of URL as ID
                    job_id = str(abs(hash(url)))
            
            if not job_id:
                # Fallback: use hash of title
                job_id = str(abs(hash(title)))
            
            # Find location
            location_elem = (
                element.find(class_=re.compile(r'location', re.I)) or
                element.find(string=re.compile(r'United States|Canada|California|Texas|Ontario', re.I))
            )
            location = ''
            if location_elem:
                if hasattr(location_elem, 'get_text'):
                    location = location_elem.get_text(strip=True)
                elif isinstance(location_elem, str):
                    location = location_elem.strip()
                else:
                    location = str(location_elem).strip()
            
            # Find date posted
            date_posted = None
            date_elem = (
                element.find(class_=re.compile(r'date|posted|posted.*date', re.I)) or
                element.find('time') or
                element.find(string=re.compile(r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}-\d{2}-\d{2}', re.I))
            )
            
            if date_elem:
                date_str = ''
                if date_elem.name == 'time' and date_elem.get('datetime'):
                    date_str = date_elem['datetime']
                elif hasattr(date_elem, 'get_text'):
                    date_str = date_elem.get_text(strip=True)
                elif isinstance(date_elem, str):
                    date_str = date_elem.strip()
                else:
                    date_str = str(date_elem).strip()
                
                if date_str:
                    date_posted = self.parse_date(date_str)
            
            # Find description
            desc_elem = element.find(class_=re.compile(r'description|summary', re.I))
            description = ''
            if desc_elem:
                description = desc_elem.get_text(strip=True)
            
            return {
                'job_id': f"amd_{job_id}",
                'title': title,
                'location': location or 'N/A',
                'description': description,
                'date_posted': date_posted or datetime.now(),
                'source': self.source_name,
                'url': url or self.base_url
            }
            
        except Exception as e:
            print(f"  Error parsing job element: {e}")
            return None
    
    def _scrape_embedded_json(self, soup):
        """Try to find JSON data embedded in script tags"""
        jobs = []
        
        try:
            # Look for JSON-LD or other JSON data
            script_tags = soup.find_all('script', type='application/json')
            script_tags.extend(soup.find_all('script', type='application/ld+json'))
            
            for script in script_tags:
                if script.string:
                    try:
                        data = json.loads(script.string)
                        # Look for job-related data
                        if isinstance(data, dict):
                            if 'jobPosting' in data or 'job' in data.lower():
                                # Try to extract jobs from structured data
                                pass
                        elif isinstance(data, list):
                            for item in data:
                                if isinstance(item, dict) and ('job' in str(item).lower() or 'position' in str(item).lower()):
                                    # Try to parse as job
                                    pass
                    except json.JSONDecodeError:
                        continue
            
            # Also look for window.__INITIAL_STATE__ or similar
            all_scripts = soup.find_all('script')
            for script in all_scripts:
                if script.string and ('job' in script.string.lower() or 'position' in script.string.lower()):
                    # Try to extract JSON from JavaScript
                    json_matches = re.findall(r'\{[^{}]*"job[^{}]*\}', script.string, re.IGNORECASE)
                    for match in json_matches[:5]:  # Limit to avoid too much processing
                        try:
                            data = json.loads(match)
                            # Try to extract job info
                        except:
                            continue
        
        except Exception as e:
            print(f"  Error extracting embedded JSON: {e}")
        
        return jobs

