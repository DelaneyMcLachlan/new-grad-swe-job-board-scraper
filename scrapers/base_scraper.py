"""
Base scraper class that all job board scrapers should inherit from
"""
from abc import ABC, abstractmethod
import requests
from datetime import datetime
import time
import config


class BaseScraper(ABC):
    """Base class for all job board scrapers"""
    
    def __init__(self, source_name, base_url):
        self.source_name = source_name
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': config.USER_AGENT
        })
    
    def fetch_page(self, url, params=None, method='GET', json_data=None, headers=None):
        """
        Fetch a page with error handling and rate limiting
        
        Args:
            url: URL to fetch
            params: Query parameters (for GET requests)
            method: HTTP method ('GET' or 'POST')
            json_data: JSON data for POST requests
            headers: Additional headers to include
        
        Returns:
            Response object or None if error
        """
        try:
            time.sleep(config.SCRAPER_DELAY_SECONDS)
            
            request_headers = self.session.headers.copy()
            if headers:
                request_headers.update(headers)
            
            if method.upper() == 'POST':
                response = self.session.post(url, json=json_data, headers=request_headers, timeout=30)
            else:
                response = self.session.get(url, params=params, headers=request_headers, timeout=30)
            
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            print(f"Error fetching {url}: {e}")
            return None
    
    @abstractmethod
    def scrape_jobs(self, filter_today_only=False, **kwargs):
        """
        Scrape jobs from the job board
        
        Args:
            filter_today_only: If True, only return jobs posted today
        
        Returns:
            list: List of dictionaries with keys: job_id, title, location, description, date_posted, url
        """
        pass
    
    def parse_date(self, date_string, date_format=None):
        """Parse date string to datetime object"""
        if not date_string:
            return None
        
        # Try common date formats
        formats = [
            '%Y-%m-%d',
            '%Y-%m-%d %H:%M:%S',
            '%m/%d/%Y',
            '%d/%m/%Y',
            '%B %d, %Y',
            '%b %d, %Y',
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%dT%H:%M:%SZ',
        ]
        
        if date_format:
            formats.insert(0, date_format)
        
        for fmt in formats:
            try:
                return datetime.strptime(date_string.strip(), fmt)
            except ValueError:
                continue
        
        # If all formats fail, return None
        print(f"Warning: Could not parse date: {date_string}")
        return None

