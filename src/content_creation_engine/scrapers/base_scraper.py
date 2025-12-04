"""
Base scraper class providing common functionality for all scrapers.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from datetime import datetime
import json
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class BaseScraper(ABC):
    """Abstract base class for all scrapers."""
    
    def __init__(self, cache_dir: Optional[Path] = None):
        """
        Initialize the base scraper.
        
        Args:
            cache_dir: Directory to store cached results
        """
        self.cache_dir = cache_dir
        if cache_dir:
            cache_dir.mkdir(parents=True, exist_ok=True)
    
    @abstractmethod
    def scrape(self, query: str, **kwargs) -> List[Dict[str, Any]]:
        """
        Perform the scraping operation.
        
        Args:
            query: Search query or topic to scrape
            **kwargs: Additional scraper-specific parameters
            
        Returns:
            List of scraped data items
        """
        pass
    
    @abstractmethod
    def get_source_name(self) -> str:
        """Return the name of the data source."""
        pass
    
    def _get_cache_key(self, query: str, **kwargs) -> str:
        """Generate a cache key for the query."""
        date_str = datetime.now().strftime("%Y-%m-%d")
        safe_query = "".join(c if c.isalnum() else "_" for c in query)
        return f"{self.get_source_name()}_{safe_query}_{date_str}"
    
    def _get_from_cache(self, cache_key: str) -> Optional[List[Dict[str, Any]]]:
        """Retrieve cached results if available and fresh."""
        if not self.cache_dir:
            return None
            
        cache_file = self.cache_dir / f"{cache_key}.json"
        if cache_file.exists():
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    cached_data = json.load(f)
                    
                # Check if cache is from today
                cache_date = cached_data.get("date")
                if cache_date == datetime.now().strftime("%Y-%m-%d"):
                    logger.info(f"Using cached data for {cache_key}")
                    return cached_data.get("results", [])
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Error reading cache: {e}")
                
        return None
    
    def _save_to_cache(self, cache_key: str, results: List[Dict[str, Any]]) -> None:
        """Save results to cache."""
        if not self.cache_dir:
            return
            
        cache_file = self.cache_dir / f"{cache_key}.json"
        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump({
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "timestamp": datetime.now().isoformat(),
                    "source": self.get_source_name(),
                    "results": results
                }, f, indent=2, ensure_ascii=False)
            logger.info(f"Cached results to {cache_file}")
        except IOError as e:
            logger.warning(f"Error saving to cache: {e}")
    
    def scrape_with_cache(self, query: str, **kwargs) -> List[Dict[str, Any]]:
        """
        Scrape with caching support.
        
        Args:
            query: Search query or topic to scrape
            **kwargs: Additional scraper-specific parameters
            
        Returns:
            List of scraped data items (from cache or fresh)
        """
        cache_key = self._get_cache_key(query, **kwargs)
        
        # Try to get from cache first
        cached_results = self._get_from_cache(cache_key)
        if cached_results is not None:
            return cached_results
        
        # Perform fresh scrape
        results = self.scrape(query, **kwargs)
        
        # Save to cache
        self._save_to_cache(cache_key, results)
        
        return results
    
    def format_results_for_prompt(self, results: List[Dict[str, Any]], max_items: int = 10) -> str:
        """
        Format results into a string suitable for AI prompts.
        
        Args:
            results: List of scraped items
            max_items: Maximum number of items to include
            
        Returns:
            Formatted string for prompt inclusion
        """
        if not results:
            return "No data available from this source."
        
        formatted_items = []
        for i, item in enumerate(results[:max_items], 1):
            formatted_item = f"{i}. "
            if "title" in item:
                formatted_item += f"**{item['title']}**"
            if "summary" in item:
                formatted_item += f"\n   {item['summary']}"
            if "url" in item:
                formatted_item += f"\n   Source: {item['url']}"
            if "engagement" in item:
                formatted_item += f"\n   Engagement: {item['engagement']}"
            formatted_items.append(formatted_item)
        
        return "\n\n".join(formatted_items)
