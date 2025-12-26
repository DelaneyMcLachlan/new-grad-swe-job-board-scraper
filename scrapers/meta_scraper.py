"""
Meta Careers scraper
Scrapes job listings from Meta careers page using GraphQL API
Uses browser automation to get session cookies, then makes GraphQL API calls
"""
import json
import re
from bs4 import BeautifulSoup
from .base_scraper import BaseScraper
from datetime import datetime
from urllib.parse import urlparse, urlencode, urljoin

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException, WebDriverException
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False


class MetaScraper(BaseScraper):
    """
    Scraper for Meta careers page
    Uses GraphQL API to fetch jobs
    """
    
    def __init__(self, base_url):
        super().__init__("meta", base_url)
        # Extract base URL
        parsed_url = urlparse(base_url)
        self.base_domain = f"{parsed_url.scheme}://{parsed_url.netloc}"
        
        # GraphQL endpoint
        self.graphql_url = f"{self.base_domain}/graphql"
        
        # Parse query parameters from URL
        query_params = {}
        if parsed_url.query:
            from urllib.parse import parse_qs
            query_params = parse_qs(parsed_url.query)
        
        # Extract roles and offices from URL
        self.roles = query_params.get('roles[0]', ['Full time employment'])
        self.offices = query_params.get('offices[0]', ['North America'])
    
    def scrape_jobs(self, filter_today_only=True, **kwargs):
        """
        Scrape jobs from Meta career page using browser automation to get session cookies
        
        Note: Meta GraphQL may not provide dates, so we don't filter by date.
        All jobs are returned and duplicate checking is handled by the database.
        
        Args:
            filter_today_only: Ignored for Meta (no dates available in API)
        
        Returns:
            list: List of job dictionaries
        """
        jobs = []
        
        if not SELENIUM_AVAILABLE:
            print("  Selenium not available. Install with: pip install selenium")
            return jobs
        
        try:
            # Use browser automation to get real session cookies
            print("  Opening browser to establish session...")
            cookies = self._get_browser_session_cookies()
            
            if cookies:
                print(f"  Got {len(cookies)} cookies from browser session")
                # Update session with cookies
                for cookie in cookies:
                    self.session.cookies.set(cookie['name'], cookie['value'], domain=cookie.get('domain', '.metacareers.com'))
                
                # Check if we intercepted jobs from browser
                if hasattr(self, '_intercepted_jobs') and self._intercepted_jobs:
                    jobs.extend(self._intercepted_jobs)
                    print(f"  Found {len(jobs)} total jobs from browser (Meta doesn't provide dates in API)")
                    return jobs
                
                # If no intercepted jobs, try GraphQL API with real cookies
                api_jobs = self._scrape_via_graphql()
                if api_jobs:
                    jobs.extend(api_jobs)
                    print(f"  Found {len(jobs)} total jobs (Meta doesn't provide dates in API)")
                    return jobs
                else:
                    print("  GraphQL API call failed even with browser cookies")
            else:
                print("  Failed to get cookies from browser session")
            
        except Exception as e:
            print(f"  Error scraping Meta jobs: {e}")
            import traceback
            traceback.print_exc()
        
        return jobs
    
    def _get_browser_session_cookies(self):
        """Use Selenium to open browser, load page, and extract cookies"""
        driver = None
        try:
            # Setup Chrome options with performance logging to intercept network requests
            chrome_options = Options()
            chrome_options.add_argument('--headless')  # Run in background
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
            
            # Enable performance logging to capture network requests
            chrome_options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})
            
            # Create driver
            driver = webdriver.Chrome(options=chrome_options)
            
            # Navigate to the page
            print("  Loading Meta careers page...")
            driver.get(self.base_url)
            
            # Wait for page to load (wait for some element that indicates jobs are loaded)
            try:
                # Wait a bit for JavaScript to execute and GraphQL calls to complete
                WebDriverWait(driver, 15).until(
                    lambda d: d.execute_script('return document.readyState') == 'complete'
                )
                # Additional wait for dynamic content and GraphQL calls
                import time
                time.sleep(8)  # Give more time for GraphQL calls to complete
            except TimeoutException:
                print("  Page load timeout, but continuing...")
            
            # Extract cookies
            cookies = driver.get_cookies()
            
            # Try to intercept GraphQL response from network logs
            # Look for the job search GraphQL request specifically
            graphql_responses = []
            try:
                logs = driver.get_log('performance')
                for log in logs:
                    try:
                        message = json.loads(log['message'])
                        if message.get('message', {}).get('method') == 'Network.responseReceived':
                            url = message.get('message', {}).get('params', {}).get('response', {}).get('url', '')
                            if 'graphql' in url.lower():
                                request_id = message.get('message', {}).get('params', {}).get('requestId')
                                if request_id:
                                    try:
                                        response_body = driver.execute_cdp_cmd('Network.getResponseBody', {'requestId': request_id})
                                        if response_body and 'body' in response_body:
                                            graphql_data = json.loads(response_body['body'])
                                            graphql_responses.append(graphql_data)
                                    except Exception as e:
                                        # CDP command might not be available or request already cleared
                                        pass
                    except:
                        continue
                
                # Check all GraphQL responses for job data
                print(f"  Found {len(graphql_responses)} GraphQL responses")
                for i, graphql_data in enumerate(graphql_responses):
                    if isinstance(graphql_data, dict) and 'data' in graphql_data:
                        data_obj = graphql_data.get('data', {})
                        # Look for job search data in various possible locations
                        if any(key in data_obj for key in ['job_search_with_featured_jobs', 'jobSearch', 'careers_job_search_results_v3']):
                            print(f"  Found job search response in GraphQL response {i+1}")
                            jobs = self._extract_jobs_from_graphql_response(graphql_data)
                            if jobs:
                                print(f"  Extracted {len(jobs)} jobs from intercepted GraphQL response")
                                self._intercepted_jobs = jobs
                                return cookies
                        else:
                            # Debug: show what we found
                            data_keys = list(data_obj.keys())
                            if 'viewer' not in data_keys:  # Skip viewer queries
                                print(f"  GraphQL response {i+1} keys: {data_keys}")
            except Exception as e:
                print(f"  Could not intercept GraphQL response: {e}")
            
            # Also try to intercept GraphQL response from network logs
            graphql_data = None
            try:
                logs = driver.get_log('performance')
                for log in reversed(logs):  # Check most recent first
                    try:
                        message = json.loads(log['message'])
                        if message.get('message', {}).get('method') == 'Network.responseReceived':
                            url = message.get('message', {}).get('params', {}).get('response', {}).get('url', '')
                            if 'graphql' in url.lower():
                                request_id = message.get('message', {}).get('params', {}).get('requestId')
                                if request_id:
                                    try:
                                        response_body = driver.execute_cdp_cmd('Network.getResponseBody', {'requestId': request_id})
                                        if response_body and 'body' in response_body:
                                            graphql_data = json.loads(response_body['body'])
                                            print("  Intercepted GraphQL response from network")
                                            break
                                    except:
                                        pass
                    except:
                        continue
                
                if graphql_data:
                    jobs = self._extract_jobs_from_graphql_response(graphql_data)
                    if jobs:
                        self._intercepted_jobs = jobs
                        return cookies
            except Exception as e:
                pass
            
            return cookies
            
        except WebDriverException as e:
            print(f"  Browser automation error: {e}")
            print("  Make sure ChromeDriver is installed and in PATH")
            return None
        except Exception as e:
            print(f"  Error getting browser cookies: {e}")
            return None
        finally:
            if driver:
                driver.quit()
    
    def _extract_jobs_from_graphql_response(self, graphql_data):
        """Extract jobs from GraphQL response"""
        jobs = []
        try:
            # Navigate through response structure
            if 'data' in graphql_data:
                data_obj = graphql_data.get('data', {})
                
                # Try multiple possible response structures
                job_search = (
                    data_obj.get('job_search_with_featured_jobs') or
                    data_obj.get('jobSearch') or
                    data_obj.get('careers_job_search_results_v3') or
                    {}
                )
                
                all_jobs = (
                    job_search.get('all_jobs') or
                    job_search.get('allJobs') or
                    job_search.get('jobs') or
                    job_search.get('edges') or
                    []
                )
                
                # If edges format (GraphQL connection pattern)
                if isinstance(all_jobs, list) and all_jobs and isinstance(all_jobs[0], dict) and 'node' in all_jobs[0]:
                    all_jobs = [edge.get('node', {}) for edge in all_jobs if edge.get('node')]
                
                if all_jobs:
                    for job_data in all_jobs:
                        job = self._parse_api_job(job_data)
                        if job:
                            jobs.append(job)
        except Exception as e:
            print(f"  Error extracting jobs from GraphQL response: {e}")
        
        return jobs
    
    def _scrape_via_graphql(self):
        """Try to scrape using Meta GraphQL API (Relay Modern with persisted queries)"""
        jobs = []
        
        # Build input from URL parameters
        roles_list = self.roles if isinstance(self.roles, list) else [self.roles]
        offices_list = self.offices if isinstance(self.offices, list) else [self.offices]
        
        # Meta uses Relay Modern with persisted queries (document IDs)
        # The query is stored on the server and referenced by doc_id
        # Based on the payload: doc_id = 24330890369943030
        # Meta uses form-encoded data, not JSON
        # Note: Some fields like __user, __a, __req, lsd might need to be extracted from the page
        # For now, use minimal required fields
        payload = {
            "fb_api_caller_class": "RelayModern",
            "fb_api_req_friendly_name": "CareersJobSearchResultsV3DataQuery",
            "server_timestamps": "true",
            "variables": json.dumps({
                "search_input": {
                    "q": None,
                    "divisions": [],
                    "offices": offices_list,
                    "roles": roles_list,
                    "leadership_levels": [],
                    "saved_jobs": [],
                    "saved_searches": [],
                    "sub_teams": [],
                    "teams": [],
                    "is_leadership": False,
                    "is_remote_only": False,
                    "sort_by_new": True,
                    "results_per_page": None
                }
            }),
            "doc_id": "24330890369943030"  # Persisted query ID for job search
        }
        
        # Try to get additional fields from page if available
        # These might be in hidden form fields or JavaScript variables
        # For now, we'll try without them first
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Origin': self.base_domain,
            'Referer': f'{self.base_domain}/jobsearch',
            'X-Requested-With': 'XMLHttpRequest',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
        }
        
        # Add cookies to headers if available
        # Use browser cookies if we have them
        if hasattr(self, '_browser_cookies') and self._browser_cookies:
            cookie_str = '; '.join([f"{c['name']}={c['value']}" for c in self._browser_cookies])
        else:
            cookie_str = '; '.join([f"{c.name}={c.value}" for c in self.session.cookies])
        
        if cookie_str:
            headers['Cookie'] = cookie_str
        
        try:
            print("  Fetching jobs via Meta GraphQL API...")
            # Meta uses form-encoded data, not JSON
            response = self.session.post(
                self.graphql_url,
                data=payload,
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    
                    # Meta's response structure may vary
                    # Try to find jobs in different possible locations
                    all_jobs = []
                    
                    # Check for jobs in response
                    if 'data' in data:
                        data_obj = data.get('data', {})
                        
                        # Try multiple possible response structures
                        job_search = (
                            data_obj.get('job_search_with_featured_jobs') or
                            data_obj.get('jobSearch') or
                            data_obj.get('job_search') or
                            data_obj.get('careers_job_search_results_v3') or
                            {}
                        )
                        
                        all_jobs = (
                            job_search.get('all_jobs') or
                            job_search.get('allJobs') or
                            job_search.get('jobs') or
                            job_search.get('edges') or
                            []
                        )
                        
                        # If edges format (GraphQL connection pattern)
                        if isinstance(all_jobs, list) and all_jobs and isinstance(all_jobs[0], dict) and 'node' in all_jobs[0]:
                            all_jobs = [edge.get('node', {}) for edge in all_jobs if edge.get('node')]
                    
                    if all_jobs:
                        print(f"  Found {len(all_jobs)} jobs via GraphQL")
                        
                        # Parse all jobs
                        for job_data in all_jobs:
                            job = self._parse_api_job(job_data)
                            if job:
                                jobs.append(job)
                        
                        if jobs:
                            return jobs
                    else:
                        # Debug: show response structure
                        print(f"  Response keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
                        if isinstance(data, dict) and 'data' in data:
                            print(f"  Data keys: {list(data['data'].keys())}")
                        if 'errors' in data:
                            print(f"  GraphQL errors: {data['errors']}")
                            
                except json.JSONDecodeError as e:
                    print(f"  JSON decode error: {e}")
                    print(f"  Response text (first 500 chars): {response.text[:500]}")
            else:
                print(f"  Status: {response.status_code}")
                print(f"  Response: {response.text[:500]}")
                
        except Exception as e:
            print(f"  Error with GraphQL request: {e}")
            import traceback
            traceback.print_exc()
        
        return jobs
    
    def _parse_api_job(self, job_data):
        """Parse a job from GraphQL API response"""
        try:
            job_id = job_data.get('id')
            title = job_data.get('title')
            
            if not job_id or not title:
                return None
            
            # Location - can be a list
            locations = job_data.get('locations', [])
            if isinstance(locations, list):
                location = ', '.join(locations) if locations else 'N/A'
            else:
                location = str(locations) if locations else 'N/A'
            
            # Teams
            teams = job_data.get('teams', [])
            sub_teams = job_data.get('sub_teams', [])
            
            # Check for date fields (Meta may not provide dates)
            date_posted = None
            date_fields = ['posted_date', 'datePosted', 'created_at', 'createdAt', 'postDate', 'published_date']
            for field in date_fields:
                if field in job_data:
                    date_str = job_data[field]
                    if date_str:
                        try:
                            if 'T' in str(date_str):
                                date_part = str(date_str).split('T')[0]
                                date_posted = datetime.strptime(date_part, '%Y-%m-%d')
                            else:
                                date_posted = self.parse_date(date_str)
                        except:
                            pass
                        if date_posted:
                            break
            
            # Construct URL
            # Meta job URLs typically: /jobs/{job_id} or /job/{job_id}
            url = f"{self.base_domain}/jobs/{job_id}"
            
            # Build description from available fields
            description_parts = []
            if teams:
                description_parts.append(f"Teams: {', '.join(teams)}")
            if sub_teams:
                description_parts.append(f"Sub-teams: {', '.join(sub_teams)}")
            description = ' | '.join(description_parts)
            
            return {
                'job_id': f"meta_{job_id}",
                'title': title,
                'location': location,
                'description': description,
                'date_posted': date_posted,  # None if not found
                'source': self.source_name,
                'url': url
            }
            
        except Exception as e:
            print(f"  Error parsing API job: {e}")
            return None
    
    def _scrape_html(self):
        """Fallback HTML scraping - extract jobs from page HTML"""
        jobs = []
        
        try:
            response = self.fetch_page(self.base_url)
            if not response:
                return jobs
            
            soup = BeautifulSoup(response.content, 'lxml')
            
            # Method 1: Look for embedded JSON data in script tags
            # Meta may embed the GraphQL response in the page
            script_tags = soup.find_all('script')
            for script in script_tags:
                if script.string:
                    script_text = script.string
                    
                    # Look for job data patterns
                    if 'all_jobs' in script_text or 'job_search' in script_text or 'jobId' in script_text:
                        # Try to find JSON data
                        # Look for patterns like: "all_jobs":[...] or {"id":"...","title":"..."}
                        try:
                            # Try to find a JSON array of jobs
                            # Pattern: array of job objects
                            job_array_pattern = r'\[[^\]]*\{[^}]*"id"\s*:\s*"[^"]+"[^}]*"title"\s*:\s*"[^"]+"[^}]*\}[^\]]*\]'
                            matches = re.finditer(job_array_pattern, script_text, re.DOTALL)
                            
                            for match in matches:
                                try:
                                    json_str = match.group(0)
                                    # Try to parse as JSON array
                                    job_list = json.loads(json_str)
                                    if isinstance(job_list, list) and job_list:
                                        for job_data in job_list:
                                            if isinstance(job_data, dict) and 'id' in job_data:
                                                job = self._parse_api_job(job_data)
                                                if job:
                                                    jobs.append(job)
                                        if jobs:
                                            print(f"  Found {len(jobs)} jobs in embedded JSON")
                                            return jobs
                                except:
                                    continue
                            
                            # Try to find the full data structure
                            # Look for "data": {...} or "job_search_with_featured_jobs": {...}
                            data_patterns = [
                                r'"data"\s*:\s*\{[^{}]*"job_search_with_featured_jobs"[^{}]*"all_jobs"\s*:\s*\[[^\]]*\]',
                                r'"job_search_with_featured_jobs"\s*:\s*\{[^{}]*"all_jobs"\s*:\s*\[[^\]]*\]',
                            ]
                            
                            for pattern in data_patterns:
                                match = re.search(pattern, script_text, re.DOTALL)
                                if match:
                                    try:
                                        # Extract larger context
                                        start = max(0, match.start() - 200)
                                        end = min(len(script_text), match.end() + 2000)
                                        json_text = script_text[start:end]
                                        
                                        # Find the start of the JSON object
                                        json_start = json_text.find('{')
                                        if json_start != -1:
                                            # Try to find matching closing brace
                                            brace_count = 0
                                            json_end = -1
                                            for i in range(json_start, len(json_text)):
                                                if json_text[i] == '{':
                                                    brace_count += 1
                                                elif json_text[i] == '}':
                                                    brace_count -= 1
                                                    if brace_count == 0:
                                                        json_end = i + 1
                                                        break
                                            
                                            if json_end != -1:
                                                json_str = json_text[json_start:json_end]
                                                data = json.loads(json_str)
                                                
                                                # Navigate to all_jobs
                                                all_jobs = (
                                                    data.get('data', {}).get('job_search_with_featured_jobs', {}).get('all_jobs') or
                                                    data.get('job_search_with_featured_jobs', {}).get('all_jobs') or
                                                    data.get('all_jobs') or
                                                    []
                                                )
                                                
                                                if all_jobs:
                                                    for job_data in all_jobs:
                                                        job = self._parse_api_job(job_data)
                                                        if job:
                                                            jobs.append(job)
                                                    if jobs:
                                                        print(f"  Found {len(jobs)} jobs in embedded JSON")
                                                        return jobs
                                    except:
                                        continue
                        except:
                            continue
            
            # Method 2: Parse HTML job listings
            job_elements = self._find_job_elements(soup)
            for element in job_elements:
                job = self._parse_job_element(element)
                if job:
                    jobs.append(job)
            
            if jobs:
                print(f"  Found {len(jobs)} jobs in HTML")
        
        except Exception as e:
            print(f"  HTML scraping failed: {e}")
            import traceback
            traceback.print_exc()
        
        return jobs
    
    def _find_job_elements(self, soup):
        """Find job listing elements in HTML"""
        # Meta might use different structures
        # Try various selectors
        job_elements = []
        
        # Try data attributes
        job_elements.extend(soup.find_all(attrs={'data-job-id': True}))
        job_elements.extend(soup.find_all(attrs={'data-jobid': True}))
        
        # Try class names
        job_elements.extend(soup.find_all('div', class_=re.compile(r'job|listing|card|position', re.I)))
        job_elements.extend(soup.find_all('li', class_=re.compile(r'job|listing|position', re.I)))
        job_elements.extend(soup.find_all('article', class_=re.compile(r'job|listing', re.I)))
        
        # Try links to job pages
        job_links = soup.find_all('a', href=re.compile(r'/job|/jobs|/careers', re.I))
        for link in job_links:
            # Get parent element
            parent = link.find_parent(['div', 'li', 'article', 'section'])
            if parent and parent not in job_elements:
                job_elements.append(parent)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_elements = []
        for elem in job_elements:
            elem_id = id(elem)
            if elem_id not in seen:
                seen.add(elem_id)
                unique_elements.append(elem)
        
        return unique_elements
    
    def _parse_job_element(self, element):
        """Parse a single job element from HTML"""
        try:
            # Find title
            title_elem = (
                element.find('h2') or
                element.find('h3') or
                element.find('a', class_=re.compile(r'title|job', re.I))
            )
            
            if not title_elem:
                return None
            
            title = title_elem.get_text(strip=True) if hasattr(title_elem, 'get_text') else str(title_elem).strip()
            if not title:
                return None
            
            # Find URL
            url = None
            link = element.find('a', href=True)
            if link:
                url = link['href']
                if not url.startswith('http'):
                    url = urljoin(self.base_domain, url)
            
            # Extract job ID from URL
            job_id = None
            if url:
                match = re.search(r'/jobs?/(\d+)', url)
                if match:
                    job_id = match.group(1)
                else:
                    job_id = str(abs(hash(url)))
            
            if not job_id:
                job_id = str(abs(hash(title)))
            
            # Find location
            location_elem = element.find(class_=re.compile(r'location', re.I))
            location = location_elem.get_text(strip=True) if location_elem else 'N/A'
            
            return {
                'job_id': f"meta_{job_id}",
                'title': title,
                'location': location,
                'description': '',
                'date_posted': None,  # Meta doesn't provide dates
                'source': self.source_name,
                'url': url or self.base_url
            }
            
        except Exception as e:
            return None

