"""
Qualcomm Careers scraper
Scrapes job listings from Qualcomm's career page
"""
import json
import re
from bs4 import BeautifulSoup
from .base_scraper import BaseScraper
from datetime import datetime
from urllib.parse import urljoin, urlparse, parse_qs, urlencode, urlunparse


class QualcommScraper(BaseScraper):
    """
    Scraper for Qualcomm careers page
    Supports scraping jobs from multiple locations (Canada, United States, etc.)
    """
    
    def __init__(self, base_url):
        super().__init__("qualcomm", base_url)
        # Qualcomm uses Eightfold.ai platform - try to find the API endpoint
        self.api_base = "https://qualcomm.eightfold.ai/api/apply/v2/jobs"
    
    def scrape_jobs(self, locations=None, filter_today_only=False, **kwargs):
        """
        Scrape jobs from Qualcomm career page
        
        Args:
            locations: List of locations to scrape (e.g., ['Canada', 'United States'])
                      If None, will try to extract from URL or scrape all
            filter_today_only: If True, only return jobs posted today
        
        Returns:
            list: List of job dictionaries
        """
        jobs = []
        
        # Determine which locations to scrape
        if locations is None:
            # Try to extract location from URL
            parsed_url = urlparse(self.base_url)
            query_params = parse_qs(parsed_url.query)
            url_location = query_params.get('location', [None])[0]
            if url_location:
                locations = [url_location]
            else:
                # Default to Canada and United States if not specified
                locations = ['Canada', 'United States']
        
        # Scrape each location
        for location in locations:
            location_jobs = self._scrape_location(location)
            jobs.extend(location_jobs)
        
        # Filter by today's date if requested
        if filter_today_only:
            today = datetime.now().date()
            filtered_jobs = []
            for job in jobs:
                if job.get('date_posted'):
                    job_date = job['date_posted']
                    if isinstance(job_date, datetime):
                        job_date = job_date.date()
                    elif isinstance(job_date, str):
                        # Try to parse the date string
                        parsed_date = self.parse_date(job_date)
                        if parsed_date:
                            job_date = parsed_date.date()
                        else:
                            continue
                    
                    if job_date == today:
                        filtered_jobs.append(job)
                else:
                    # If no date, skip it (we only want jobs with dates)
                    continue
            jobs = filtered_jobs
        
        return jobs
    
    def _scrape_location(self, location):
        """Scrape jobs for a specific location"""
        jobs = []
        
        # Method 1: Try to use the API endpoint directly
        api_jobs = self._try_api_scrape(location)
        if api_jobs:
            return api_jobs
        
        # Method 2: Parse HTML page
        html_jobs = self._scrape_html(location)
        if html_jobs:
            return html_jobs
        
        # Method 3: Try to find JSON data embedded in the page
        embedded_jobs = self._scrape_embedded_json(location)
        if embedded_jobs:
            return embedded_jobs
        
        return jobs
    
    def _try_api_scrape(self, location):
        """Try to scrape using API endpoint"""
        jobs = []
        
        try:
            # Try common API patterns for Eightfold.ai
            api_urls = [
                f"{self.api_base}?location={location}",
                f"https://qualcomm.eightfold.ai/api/apply/v2/jobs?q=&location={location}",
                f"https://qualcomm.eightfold.ai/api/apply/v2/jobs?domain=qualcomm.com&location={location}",
            ]
            
            for api_url in api_urls:
                response = self.fetch_page(api_url)
                if response:
                    try:
                        data = response.json()
                        if 'positions' in data or 'jobs' in data or 'results' in data:
                            positions = data.get('positions') or data.get('jobs') or data.get('results') or []
                            for pos in positions:
                                job = self._parse_api_job(pos, location)
                                if job:
                                    jobs.append(job)
                            if jobs:
                                return jobs
                    except (json.JSONDecodeError, KeyError):
                        continue
        except Exception as e:
            print(f"  API scrape failed: {e}")
        
        return jobs
    
    def _scrape_html(self, location):
        """Scrape jobs from HTML page"""
        jobs = []
        
        try:
            # Build URL with location parameter
            parsed_url = urlparse(self.base_url)
            query_params = parse_qs(parsed_url.query)
            query_params['location'] = [location]
            new_query = urlencode(query_params, doseq=True)
            new_url = urlunparse((
                parsed_url.scheme,
                parsed_url.netloc,
                parsed_url.path,
                parsed_url.params,
                new_query,
                parsed_url.fragment
            ))
            
            response = self.fetch_page(new_url)
            if not response:
                return jobs
            
            soup = BeautifulSoup(response.content, 'lxml')
            
            # Look for job listings - Eightfold.ai typically uses specific classes
            # Common patterns: position-card, job-card, position-item, etc.
            job_selectors = [
                {'class': 'position-card'},
                {'class': 'job-card'},
                {'class': 'position-item'},
                {'class': 'job-item'},
                {'data-testid': 'position-card'},
            ]
            
            job_listings = []
            for selector in job_selectors:
                job_listings = soup.find_all('div', selector)
                if job_listings:
                    break
            
            # Also try finding by data attributes
            if not job_listings:
                job_listings = soup.find_all(attrs={'data-position-id': True})
            
            for listing in job_listings:
                try:
                    job = self._parse_html_job(listing, location)
                    if job:
                        jobs.append(job)
                except Exception as e:
                    print(f"  Error parsing HTML job: {e}")
                    continue
                    
        except Exception as e:
            print(f"  HTML scrape failed: {e}")
        
        return jobs
    
    def _scrape_embedded_json(self, location):
        """Try to extract JSON data embedded in script tags"""
        jobs = []
        
        try:
            parsed_url = urlparse(self.base_url)
            query_params = parse_qs(parsed_url.query)
            query_params['location'] = [location]
            new_query = urlencode(query_params, doseq=True)
            new_url = urlunparse((
                parsed_url.scheme,
                parsed_url.netloc,
                parsed_url.path,
                parsed_url.params,
                new_query,
                parsed_url.fragment
            ))
            
            response = self.fetch_page(new_url)
            if not response:
                return jobs
            
            # Look for JSON in script tags
            soup = BeautifulSoup(response.content, 'lxml')
            script_tags = soup.find_all('script', type='application/json')
            script_tags.extend(soup.find_all('script', string=re.compile(r'positions|jobs|results')))
            
            for script in script_tags:
                try:
                    if script.string:
                        # Try to extract JSON from script content
                        json_match = re.search(r'\{.*"positions".*\}', script.string, re.DOTALL)
                        if json_match:
                            data = json.loads(json_match.group())
                            if 'positions' in data or 'jobs' in data:
                                positions = data.get('positions') or data.get('jobs') or []
                                for pos in positions:
                                    job = self._parse_api_job(pos, location)
                                    if job:
                                        jobs.append(job)
                                if jobs:
                                    return jobs
                except (json.JSONDecodeError, AttributeError):
                    continue
            
            # Also try to find window.__INITIAL_STATE__ or similar
            page_text = response.text
            state_patterns = [
                r'window\.__INITIAL_STATE__\s*=\s*(\{.*?\});',
                r'window\.__APOLLO_STATE__\s*=\s*(\{.*?\});',
                r'positions\s*:\s*(\[.*?\])',
            ]
            
            for pattern in state_patterns:
                matches = re.findall(pattern, page_text, re.DOTALL)
                for match in matches:
                    try:
                        data = json.loads(match)
                        if isinstance(data, list):
                            for pos in data:
                                job = self._parse_api_job(pos, location)
                                if job:
                                    jobs.append(job)
                        elif isinstance(data, dict) and ('positions' in data or 'jobs' in data):
                            positions = data.get('positions') or data.get('jobs') or []
                            for pos in positions:
                                job = self._parse_api_job(pos, location)
                                if job:
                                    jobs.append(job)
                        if jobs:
                            return jobs
                    except (json.JSONDecodeError, KeyError):
                        continue
                        
        except Exception as e:
            print(f"  Embedded JSON scrape failed: {e}")
        
        return jobs
    
    def _parse_api_job(self, job_data, location):
        """Parse a job from API JSON response"""
        try:
            # Extract job ID - try various field names
            job_id = (
                job_data.get('id') or 
                job_data.get('job_id') or 
                job_data.get('position_id') or
                job_data.get('name') or
                str(job_data.get('name', '')) + '_' + str(job_data.get('id', ''))
            )
            
            if not job_id:
                return None
            
            # Extract title
            title = (
                job_data.get('name') or
                job_data.get('title') or
                job_data.get('position_title') or
                job_data.get('job_title') or
                "N/A"
            )
            
            # Extract location
            job_location = (
                job_data.get('location') or
                job_data.get('city') or
                job_data.get('locations', [{}])[0].get('location') if isinstance(job_data.get('locations'), list) else None or
                location
            )
            
            # Extract description
            description = (
                job_data.get('description') or
                job_data.get('job_description') or
                job_data.get('summary') or
                job_data.get('requisition_description') or
                ""
            )
            
            # Extract date
            date_posted = None
            date_str = (
                job_data.get('posted_date') or
                job_data.get('created_date') or
                job_data.get('date_posted') or
                job_data.get('postedOn')
            )
            if date_str:
                date_posted = self.parse_date(date_str)
            
            # Extract URL first
            url = (
                job_data.get('url') or
                job_data.get('apply_url') or
                job_data.get('job_url') or
                None
            )
            
            # Extract real job ID from URL if available (format: /job/446715960276)
            # This ensures we use the actual job ID from the URL
            if url and '/job/' in url:
                url_match = re.search(r'/job/(\d+)', url)
                if url_match:
                    real_job_id = url_match.group(1)
                    # Use the real job ID from URL
                    job_id = real_job_id
                    # Ensure URL is complete
                    if not url.startswith('http'):
                        url = f"https://qualcomm.eightfold.ai{url}" if url.startswith('/') else f"https://qualcomm.eightfold.ai/{url}"
            elif not url:
                # Construct URL from job_id if we have it
                url = f"https://qualcomm.eightfold.ai/careers/job/{job_id}"
            
            return {
                'job_id': f"qualcomm_{job_id}",
                'title': title,
                'location': job_location,
                'description': description,
                'date_posted': date_posted or datetime.now(),
                'source': self.source_name,
                'url': url
            }
        except Exception as e:
            print(f"  Error parsing API job: {e}")
            return None
    
    def _parse_html_job(self, listing, location):
        """Parse a job from HTML listing"""
        try:
            # Extract job ID
            job_id = (
                listing.get('data-position-id') or
                listing.get('data-job-id') or
                listing.get('id') or
                None
            )
            
            # Extract title
            title_elem = (
                listing.find('h2') or
                listing.find('h3') or
                listing.find('a', class_=re.compile(r'title|position'))
            )
            title = title_elem.text.strip() if title_elem else "N/A"
            
            # Extract location
            location_elem = listing.find(attrs={'class': re.compile(r'location')})
            job_location = location_elem.text.strip() if location_elem else location
            
            # Extract description
            desc_elem = (
                listing.find('div', class_=re.compile(r'description|summary')) or
                listing.find('p', class_=re.compile(r'description|summary'))
            )
            description = desc_elem.text.strip() if desc_elem else ""
            
            # Extract date
            date_elem = listing.find('time') or listing.find(attrs={'class': re.compile(r'date')})
            date_posted = None
            if date_elem:
                date_str = date_elem.get('datetime') or date_elem.text.strip()
                date_posted = self.parse_date(date_str)
            
            # Extract URL
            link_elem = listing.find('a', href=True)
            url = None
            if link_elem:
                url = link_elem['href']
                if not url.startswith('http'):
                    url = urljoin('https://qualcomm.eightfold.ai', url)
            
            # Extract real job ID from URL if available (format: /job/446715960276)
            if url and '/job/' in url:
                url_match = re.search(r'/job/(\d+)', url)
                if url_match:
                    job_id = url_match.group(1)
            
            # Generate job_id if not found
            if not job_id:
                if url:
                    # Try to extract from URL one more time
                    url_match = re.search(r'/job/(\d+)', url)
                    if url_match:
                        job_id = url_match.group(1)
                    else:
                        job_id = str(abs(hash(url)))
                else:
                    job_id = str(abs(hash(title + job_location)))
            
            return {
                'job_id': f"qualcomm_{job_id}",
                'title': title,
                'location': job_location,
                'description': description,
                'date_posted': date_posted or datetime.now(),
                'source': self.source_name,
                'url': url or self.base_url
            }
        except Exception as e:
            print(f"  Error parsing HTML job: {e}")
            return None

