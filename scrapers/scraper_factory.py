"""
Factory for creating scraper instances based on job board name
"""
from .qualcomm_scraper import QualcommScraper
from .workday_scraper import WorkdayScraper
from .amd_scraper import AMDScraper
from .synopsys_scraper import SynopsysScraper
from .meta_scraper import MetaScraper
from .google_scraper import GoogleScraper
from .ti_scraper import TIScraper
# Import other scrapers here as you create them
# from .indeed_scraper import IndeedScraper
# from .linkedin_scraper import LinkedInScraper


class ScraperFactory:
    """Factory to create appropriate scraper instances"""
    
    _scrapers = {
        'qualcomm': QualcommScraper,
        'workday': WorkdayScraper,  # Generic Workday scraper
        'nvidia': WorkdayScraper,   # NVIDIA uses Workday
        'cadence': WorkdayScraper,  # Cadence uses Workday
        'amd': AMDScraper,          # AMD careers scraper
        'synopsys': SynopsysScraper,  # Synopsys careers scraper
        'meta': MetaScraper,         # Meta careers scraper
        'google': GoogleScraper,     # Google careers scraper
        'ti': TIScraper,             # Texas Instruments careers scraper
        'texas_instruments': TIScraper,  # Alternative name
        # Add mappings here as you create new scrapers
        # 'indeed': IndeedScraper,
        # 'linkedin': LinkedInScraper,
    }
    
    @classmethod
    def _detect_scraper_type(cls, base_url):
        """
        Auto-detect scraper type based on URL
        Returns scraper class name or None
        """
        url_lower = base_url.lower()
        
        # Check for Workday
        if 'myworkdayjobs.com' in url_lower:
            return 'workday'
        
        # Check for specific companies
        if 'qualcomm' in url_lower:
            return 'qualcomm'
        
        if 'amd.com' in url_lower or 'careers.amd.com' in url_lower:
            return 'amd'
        
        if 'synopsys.com' in url_lower or 'careers.synopsys.com' in url_lower:
            return 'synopsys'
        
        if 'metacareers.com' in url_lower or 'meta.com' in url_lower:
            return 'meta'
        
        if 'google.com/about/careers' in url_lower or 'google.com/careers' in url_lower:
            return 'google'
        
        if 'careers.ti.com' in url_lower or 'ti.com' in url_lower:
            return 'ti'
        
        return None
    
    @classmethod
    def create_scraper(cls, board_name, base_url):
        """
        Create a scraper instance for the given job board
        
        Args:
            board_name: Name of the job board (must be registered)
            base_url: Base URL for the job board
        
        Returns:
            BaseScraper instance or None if board_name not found
        """
        # Try exact match first
        scraper_class = cls._scrapers.get(board_name.lower())
        
        # If not found, try auto-detection
        if not scraper_class:
            detected_type = cls._detect_scraper_type(base_url)
            if detected_type:
                scraper_class = cls._scrapers.get(detected_type)
                if scraper_class:
                    print(f"  Auto-detected {detected_type} scraper for {board_name}")
        
        if scraper_class:
            return scraper_class(base_url)
        else:
            print(f"Warning: No scraper found for '{board_name}'. Available scrapers: {list(cls._scrapers.keys())}")
            return None
    
    @classmethod
    def register_scraper(cls, board_name, scraper_class):
        """Register a new scraper class"""
        cls._scrapers[board_name.lower()] = scraper_class

