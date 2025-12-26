"""
Generic Workday job board scraper
Works with any company using Workday's job board platform
"""
import json
import re
from bs4 import BeautifulSoup
from .base_scraper import BaseScraper
from datetime import datetime
from urllib.parse import urlparse, parse_qs


class WorkdayScraper(BaseScraper):
    """
    Generic scraper for Workday job boards
    Works with any company using Workday (e.g., NVIDIA, Apple, etc.)
    """
    
    def __init__(self, base_url):
        # Extract company name and site from URL
        parsed_url = urlparse(base_url)
        hostname_parts = parsed_url.netloc.split('.')
        
        # Extract company name (e.g., "nvidia" from "nvidia.wd5.myworkdayjobs.com")
        company_name = hostname_parts[0] if hostname_parts else 'company'
        
        # Extract site name from path (e.g., "NVIDIAExternalCareerSite")
        site_name = parsed_url.path.strip('/').split('/')[-1] if parsed_url.path else 'ExternalCareerSite'
        
        # Use company name as source
        source_name = company_name.lower()
        super().__init__(source_name, base_url)
        
        self.company_name = company_name
        self.site_name = site_name
        
        # Construct API endpoint
        # Format: https://company.wd5.myworkdayjobs.com/wday/cxs/company/SiteName/jobs
        self.api_endpoint = f"https://{parsed_url.netloc}/wday/cxs/{company_name}/{site_name}/jobs"
        
        # Extract filters from URL query parameters
        self.url_filters = parse_qs(parsed_url.query)
    
    def scrape_jobs(self, filter_today_only=True, **kwargs):
        """
        Scrape jobs from Workday job board
        
        Args:
            filter_today_only: If True, only return jobs posted today
        
        Returns:
            list: List of job dictionaries
        """
        jobs = []
        
        try:
            # Try API method first (most reliable)
            # Pass filter_today_only so API can stop early when it encounters older jobs
            api_jobs = self._scrape_via_api(filter_today_only=filter_today_only)
            if api_jobs:
                jobs.extend(api_jobs)
            
            # Fallback to HTML scraping if API fails
            if not jobs:
                html_jobs = self._scrape_via_html()
                if html_jobs:
                    jobs.extend(html_jobs)
                    # Filter HTML jobs if needed
                    if filter_today_only:
                        filtered_jobs = []
                        for job in jobs:
                            raw_date = job.get('date_posted_raw', '')
                            if raw_date:
                                raw_date_lower = raw_date.lower().strip()
                                if raw_date_lower == 'posted today' or raw_date_lower.startswith('posted today'):
                                    filtered_jobs.append(job)
                        jobs = filtered_jobs
            
        except Exception as e:
            print(f"  Error scraping Workday jobs: {e}")
        
        return jobs
    
    def _scrape_via_api(self, filter_today_only=True):
        """
        Scrape jobs using Workday API
        
        Args:
            filter_today_only: If True, stop parsing once we encounter a job that's not "Posted Today"
                              (since jobs are sorted newest to oldest)
        """
        jobs = []
        
        try:
            # Workday API uses POST requests
            # Try with filters first, but fall back to no filters if that fails
            applied_filters = []
            
            # Convert URL query params to Workday filter format (if any)
            # Workday expects filters grouped by name
            if self.url_filters:
                filter_dict = {}
                for key, values in self.url_filters.items():
                    if key not in filter_dict:
                        filter_dict[key] = []
                    # parse_qs returns lists, so extend with the list
                    filter_dict[key].extend(values)
                
                # Build appliedFacets array - group values by filter name
                for filter_name, filter_values in filter_dict.items():
                    applied_filters.append({
                        "name": filter_name,
                        "values": filter_values
                    })
            
            # Set headers for API request
            headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'User-Agent': self.session.headers['User-Agent']
            }
            
            # Try with filters first
            payload_with_filters = {
                "appliedFacets": applied_filters,
                "limit": 20,
                "offset": 0,
                "searchText": ""
            }
            
            # Try without filters as fallback (Workday API sometimes rejects filter format)
            payload_no_filters = {
                "limit": 20,
                "offset": 0,
                "searchText": ""
            }
            
            if applied_filters:
                print(f"  Applying {len(applied_filters)} filter(s) from URL")
            
            # Try with filters first
            if applied_filters:
                response = self.session.post(
                    self.api_endpoint,
                    json=payload_with_filters,
                    headers=headers,
                    timeout=30
                )
                print(f"  Status: {response.status_code}")
                
                # Check if response is valid
                if response.status_code == 200:
                    try:
                        data = response.json()
                        # Check if response has expected structure
                        if 'jobPostings' in data or 'total' in data:
                            payload = payload_with_filters
                        else:
                            print(f"  Warning: Unexpected response structure. Keys: {list(data.keys())}")
                            payload = payload_with_filters
                    except json.JSONDecodeError:
                        print(f"  Error: Response is not valid JSON")
                        print(f"  Response text: {response.text[:500]}")
                        raise Exception("API returned invalid JSON response")
                else:
                    # Filters failed - fall back to no filters
                    print(f"  Filters failed, trying without filters...")
                    response = self.session.post(
                        self.api_endpoint,
                        json=payload_no_filters,
                        headers=headers,
                        timeout=30
                    )
                    print(f"  Status (no filters): {response.status_code}")
                    payload = payload_no_filters
            else:
                # No filters to apply - use simple payload
                response = self.session.post(
                    self.api_endpoint,
                    json=payload_no_filters,
                    headers=headers,
                    timeout=30
                )
                print(f"  Status: {response.status_code}")
                payload = payload_no_filters
                
                if response.status_code != 200:
                    print(f"  Error: API call failed with status {response.status_code}")
                    print(f"  Response: {response.text[:500]}")
                    return jobs
            
            if response.status_code == 200:
                data = response.json()
                
                total = data.get('total', 0)
                job_postings = data.get('jobPostings', [])
                
                print(f"  Found {total} total jobs, {len(job_postings)} in first page")
                
                # Handle pagination
                limit = payload['limit']
                
                if total == 0:
                    print(f"  Warning: API returned 0 total jobs. Response keys: {list(data.keys())}")
                    return jobs
                
                # If we got jobs without filters, we'll need to filter them manually later
                # But for now, let's get all pages
                
                # Get all pages if needed
                # If filter_today_only is True, stop once we encounter a job that's not "Posted Today"
                parsed_count = 0
                skipped_count = 0
                found_non_today_job = False
                
                while len(jobs) < total and len(job_postings) > 0 and not found_non_today_job:
                    for posting in job_postings:
                        job = self._parse_workday_job(posting)
                        if job:
                            # If filtering for today only, check the date
                            if filter_today_only:
                                raw_date = job.get('date_posted_raw', '')
                                if raw_date:
                                    raw_date_lower = raw_date.lower().strip()
                                    # Check if it's "Posted Today"
                                    if raw_date_lower == 'posted today' or raw_date_lower.startswith('posted today'):
                                        jobs.append(job)
                                        parsed_count += 1
                                    else:
                                        # Found a job that's not "Posted Today" - stop parsing
                                        # (jobs are sorted newest to oldest)
                                        found_non_today_job = True
                                        print(f"  Found job with '{raw_date}' - stopping (jobs are sorted newest to oldest)")
                                        break
                                else:
                                    # No date info, skip it
                                    skipped_count += 1
                            else:
                                # Not filtering, add all jobs
                                jobs.append(job)
                                parsed_count += 1
                        else:
                            skipped_count += 1
                    
                    # If we found a non-today job, stop pagination
                    if found_non_today_job:
                        break
                    
                    # Show progress (only if parsing many jobs)
                    if not filter_today_only and len(jobs) % 50 == 0:
                        print(f"  Parsed {len(jobs)} jobs so far...")
                    
                    # Check if there are more pages
                    if len(jobs) < total and not found_non_today_job:
                        payload['offset'] += limit
                        response = self.session.post(
                            self.api_endpoint,
                            json=payload,
                            headers=headers,
                            timeout=30
                        )
                        if response.status_code == 200:
                            data = response.json()
                            job_postings = data.get('jobPostings', [])
                        else:
                            break
                    else:
                        break
                
                if filter_today_only:
                    print(f"  Found {len(jobs)} job(s) posted today")
                else:
                    print(f"  Parsed {len(jobs)} jobs")
                
                if jobs:
                    return jobs
            
        except Exception as e:
            print(f"  API scrape failed: {e}")
            import traceback
            traceback.print_exc()
        
        return jobs
    
    def _scrape_via_html(self):
        """Fallback: Scrape jobs from HTML page"""
        jobs = []
        
        try:
            print(f"  Attempting HTML scrape from: {self.base_url}")
            response = self.fetch_page(self.base_url)
            if not response:
                print(f"  Failed to fetch HTML page")
                return jobs
            
            print(f"  HTML page fetched successfully ({len(response.content)} bytes)")
            soup = BeautifulSoup(response.content, 'lxml')
            
            # Look for job listings in HTML
            # Workday typically uses data attributes or specific classes
            print(f"  Searching for job listings...")
            
            # Try multiple selectors
            job_listings = soup.find_all(attrs={'data-automation-id': re.compile(r'jobTitle|jobPosting|job', re.I)})
            
            if not job_listings:
                # Try alternative selectors - Workday uses various patterns
                job_listings = soup.find_all('li', class_=re.compile(r'job|posting|result', re.I))
            
            if not job_listings:
                # Try finding by data-job-id or similar
                job_listings = soup.find_all(attrs={'data-job-id': True})
            
            if not job_listings:
                # Try finding links that look like job links
                job_listings = soup.find_all('a', href=re.compile(r'/job|/jobs|/careers', re.I))
            
            print(f"  Found {len(job_listings)} potential job listings")
            
            # Also look for JSON data embedded in the page
            script_tags = soup.find_all('script', type='application/json')
            if script_tags:
                print(f"  Found {len(script_tags)} JSON script tags - checking for job data...")
                for script in script_tags:
                    try:
                        if script.string:
                            script_data = json.loads(script.string)
                            # Look for job-related data
                            if 'jobPostings' in script_data or 'jobs' in script_data:
                                print(f"  Found job data in script tag!")
                                job_data_list = script_data.get('jobPostings') or script_data.get('jobs') or []
                                for job_data in job_data_list:
                                    job = self._parse_workday_job(job_data)
                                    if job:
                                        jobs.append(job)
                    except (json.JSONDecodeError, KeyError):
                        continue
            
            # Parse HTML listings
            for listing in job_listings:
                try:
                    job = self._parse_html_job(listing)
                    if job:
                        jobs.append(job)
                except Exception as e:
                    print(f"  Error parsing HTML job: {e}")
                    continue
            
            print(f"  HTML scrape found {len(jobs)} jobs")
                    
        except Exception as e:
            print(f"  HTML scrape failed: {e}")
            import traceback
            traceback.print_exc()
        
        return jobs
    
    def _parse_workday_job(self, job_data):
        """Parse a job from Workday API response"""
        try:
            # Extract job ID - try multiple fields
            job_id = (
                job_data.get('jobId') or
                job_data.get('jobPostingId') or
                job_data.get('externalPath') or
                (job_data.get('title', {}) if isinstance(job_data.get('title'), dict) else {}).get('commandLink', '') or
                job_data.get('id', '')
            )
            
            # If still no job_id, try to generate one from URL or title
            if not job_id:
                # Try to get from externalPath
                external_path = job_data.get('externalPath', '')
                if external_path:
                    # Extract ID from path (e.g., "/job/12345" -> "12345")
                    match = re.search(r'/(\d+)/?$', external_path)
                    if match:
                        job_id = match.group(1)
                    else:
                        job_id = external_path.split('/')[-1] if '/' in external_path else external_path
                
                # Last resort: use title hash
                if not job_id:
                    title_data = job_data.get('title', {})
                    if isinstance(title_data, dict):
                        title = title_data.get('instances', [{}])[0].get('text', '') or title_data.get('commandLink', '')
                    else:
                        title = str(title_data)
                    if title:
                        job_id = str(abs(hash(title)))
                    else:
                        return None
            
            # Extract title
            title_data = job_data.get('title', {})
            if isinstance(title_data, dict):
                title = title_data.get('instances', [{}])[0].get('text') or title_data.get('commandLink', '')
            else:
                title = str(title_data)
            
            if not title:
                return None
            
            # Extract location
            locations = job_data.get('locationsText', {})
            if isinstance(locations, dict):
                location = locations.get('instances', [{}])[0].get('text', '')
            else:
                location = str(locations) if locations else ''
            
            # Extract description
            description = job_data.get('jobDescription', {}).get('instances', [{}])[0].get('text', '')
            if not description:
                description = job_data.get('jobDescription', '')
            
            # Extract date posted
            # Workday uses human-readable format like "Posted Today", "Posted Yesterday", etc.
            date_posted = None
            posted_on = job_data.get('postedOn', '')
            
            # Handle different formats - could be string or dict
            if isinstance(posted_on, dict):
                # Try to extract from nested structure
                date_str = posted_on.get('instances', [{}])[0].get('text', '') if posted_on.get('instances') else ''
                if not date_str:
                    date_str = str(posted_on.get('text', ''))
            else:
                # It's a string like "Posted Today"
                date_str = str(posted_on).strip() if posted_on else ''
            
            # Store the raw date string for filtering
            raw_date_str = date_str
            
            # Check if it says "Posted Today" (case-insensitive)
            if date_str and 'today' in date_str.lower():
                # If it says "Posted Today", set to today's date
                date_posted = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            elif date_str:
                # Check if it's a relative date (Posted Yesterday, Posted 2 days ago, etc.)
                # Don't try to parse these - they're not actual dates
                date_lower = date_str.lower().strip()
                if date_lower.startswith('posted'):
                    # It's a relative date string, don't try to parse it
                    # Just use current date as fallback
                    date_posted = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                else:
                    # Try to parse if it's a real date format
                    parsed_date = self.parse_date(date_str)
                    if parsed_date:
                        date_posted = parsed_date
            
            # Extract URL - Workday URLs need format: /en-US/SiteName/details/job-path
            # The externalPath from API might be like: /job/Location/Job-Title_ID
            # We need to convert it to: /en-US/SiteName/details/Job-Title_ID
            url = job_data.get('externalPath', '')
            parsed_base = urlparse(self.base_url)
            
            if url:
                if url.startswith('http'):
                    # Already a full URL - check if it needs conversion
                    if '/job/' in url:
                        # Convert /job/... to /en-US/.../details/...
                        # Extract the job identifier part (last segment after /job/)
                        parts = url.split('/job/')
                        if len(parts) > 1:
                            job_part = parts[1].split('/')[-1]  # Get last part (Job-Title_ID)
                            url = f"{parsed_base.scheme}://{parsed_base.netloc}/en-US/{self.site_name}/details/{job_part}"
                    elif '/en-US/' not in url:
                        # Full URL but not in correct format - try to extract job path
                        job_part = url.split('/')[-1]
                        url = f"{parsed_base.scheme}://{parsed_base.netloc}/en-US/{self.site_name}/details/{job_part}"
                elif url.startswith('/job/'):
                    # Path like /job/Location/Job-Title_ID - extract job identifier
                    job_part = url.split('/')[-1]  # Get last segment (Job-Title_ID)
                    url = f"{parsed_base.scheme}://{parsed_base.netloc}/en-US/{self.site_name}/details/{job_part}"
                elif url.startswith('/en-US/'):
                    # Already in correct format
                    url = f"{parsed_base.scheme}://{parsed_base.netloc}{url}"
                elif url.startswith('/'):
                    # Other relative path - try to use as-is but ensure /en-US/ format
                    if '/details/' in url:
                        url = f"{parsed_base.scheme}://{parsed_base.netloc}{url}"
                    else:
                        # Extract job identifier
                        job_part = url.strip('/').split('/')[-1]
                        url = f"{parsed_base.scheme}://{parsed_base.netloc}/en-US/{self.site_name}/details/{job_part}"
                else:
                    # Just a job identifier - construct full path
                    url = f"{parsed_base.scheme}://{parsed_base.netloc}/en-US/{self.site_name}/details/{url}"
            else:
                # No externalPath - construct from job ID
                # The job_id might be like "Job-Title_ID" or just an ID
                job_path = str(job_id)
                # Remove any path separators
                if '/' in job_path:
                    job_path = job_path.split('/')[-1]
                url = f"{parsed_base.scheme}://{parsed_base.netloc}/en-US/{self.site_name}/details/{job_path}"
            
            # Clean up job_id - extract numeric ID if it's a path
            if '/' in str(job_id):
                job_id = str(job_id).split('/')[-1]
            
            return {
                'job_id': f"{self.source_name}_{job_id}",
                'title': title,
                'location': location or 'N/A',
                'description': description or '',
                'date_posted': date_posted or datetime.now(),
                'date_posted_raw': raw_date_str,  # Store raw string for filtering
                'source': self.source_name,
                'url': url or self.base_url
            }
            
        except Exception as e:
            print(f"  Error parsing Workday job: {e}")
            return None
    
    def _parse_html_job(self, listing):
        """Parse a job from HTML listing (fallback method)"""
        try:
            # Extract job ID
            job_id = (
                listing.get('data-job-id') or
                listing.get('data-automation-id') or
                listing.get('id') or
                None
            )
            
            # Extract title
            title_elem = listing.find(attrs={'data-automation-id': 'jobTitle'})
            if not title_elem:
                title_elem = listing.find('a', href=True) or listing.find('h2') or listing.find('h3')
            
            title = title_elem.text.strip() if title_elem else "N/A"
            
            # Extract location
            location_elem = listing.find(attrs={'data-automation-id': 'jobLocation'})
            if not location_elem:
                location_elem = listing.find(attrs={'class': re.compile(r'location', re.I)})
            
            location = location_elem.text.strip() if location_elem else 'N/A'
            
            # Extract description
            desc_elem = listing.find(attrs={'data-automation-id': 'jobDescription'})
            if not desc_elem:
                desc_elem = listing.find(attrs={'class': re.compile(r'description', re.I)})
            
            description = desc_elem.text.strip() if desc_elem else ''
            
            # Extract date
            date_elem = listing.find(attrs={'data-automation-id': 'jobPostedDate'})
            if not date_elem:
                date_elem = listing.find('time') or listing.find(attrs={'class': re.compile(r'date', re.I)})
            
            date_posted = None
            raw_date_str = ''
            if date_elem:
                # Get the raw text first (e.g., "Posted Today", "Posted Yesterday")
                raw_date_str = date_elem.text.strip() if date_elem.text else ''
                if not raw_date_str:
                    raw_date_str = date_elem.get('datetime', '')
                
                # Check if it says "Posted Today"
                if raw_date_str and 'today' in raw_date_str.lower():
                    date_posted = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                elif raw_date_str:
                    # Check if it's a relative date (Posted Yesterday, Posted 2 days ago, etc.)
                    date_lower = raw_date_str.lower().strip()
                    if date_lower.startswith('posted'):
                        # It's a relative date string, don't try to parse it
                        date_posted = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                    else:
                        # Try to parse if it's a real date format
                        date_str = date_elem.get('datetime') or raw_date_str
                        date_posted = self.parse_date(date_str)
            
            # Extract URL - ensure it uses /en-US/SiteName/details/ format
            link_elem = listing.find('a', href=True)
            url = None
            parsed_base = urlparse(self.base_url)
            
            if link_elem:
                url = link_elem['href']
                if not url.startswith('http'):
                    # If it's a relative path, check if it already has /en-US/
                    if url.startswith('/en-US/'):
                        url = f"{parsed_base.scheme}://{parsed_base.netloc}{url}"
                    elif url.startswith('/'):
                        # Path like /job/123 or /details/... - ensure it has /en-US/SiteName/details/
                        if '/details/' in url:
                            url = f"{parsed_base.scheme}://{parsed_base.netloc}/en-US/{self.site_name}{url}"
                        else:
                            # Extract job path and construct properly
                            job_path = url.strip('/').split('/')[-1]
                            url = f"{parsed_base.scheme}://{parsed_base.netloc}/en-US/{self.site_name}/details/{job_path}"
                    else:
                        # Just a job identifier
                        url = f"{parsed_base.scheme}://{parsed_base.netloc}/en-US/{self.site_name}/details/{url}"
            
            # Generate job_id if not found
            if not job_id:
                if url:
                    # Extract ID from URL
                    url_match = re.search(r'/(\d+)/', url)
                    if url_match:
                        job_id = url_match.group(1)
                    else:
                        job_id = str(abs(hash(url)))
                else:
                    job_id = str(abs(hash(title + location)))
            
            return {
                'job_id': f"{self.source_name}_{job_id}",
                'title': title,
                'location': location,
                'description': description,
                'date_posted': date_posted or datetime.now(),
                'date_posted_raw': raw_date_str,  # Store raw string for filtering (e.g., "Posted Today")
                'source': self.source_name,
                'url': url or self.base_url
            }
            
        except Exception as e:
            print(f"  Error parsing HTML job: {e}")
            return None

