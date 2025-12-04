"""
News scraper using NewsAPI.
Fetches recent news articles related to the content niche.
"""

from typing import Any, Dict, List, Optional
from pathlib import Path
from datetime import datetime, timedelta
import logging

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class NewsScraper(BaseScraper):
    """Scraper for news articles using NewsAPI."""
    
    # Keywords to add for different niches to improve search results
    NICHE_KEYWORDS = {
        "sat": ["SAT exam", "college admissions", "standardized testing", "test prep"],
        "sat exam preparation": ["SAT exam", "college admissions", "SAT scores", "test prep"],
        "fitness": ["workout", "exercise", "health", "gym"],
        "cooking": ["recipes", "food trends", "cooking tips", "culinary"],
        "programming": ["software development", "coding", "tech", "developers"],
        "personal finance": ["money management", "investing", "savings", "financial planning"],
    }
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://newsapi.org/v2",
        cache_dir: Optional[Path] = None
    ):
        """
        Initialize News scraper.
        
        Args:
            api_key: NewsAPI API key
            base_url: Base URL for NewsAPI
            cache_dir: Directory for caching results
        """
        super().__init__(cache_dir)
        
        self.api_key = api_key
        self.base_url = base_url
    
    def get_source_name(self) -> str:
        return "news"
    
    def _get_keywords_for_niche(self, niche: str) -> List[str]:
        """Get additional search keywords for a niche."""
        niche_lower = niche.lower()
        
        for key, keywords in self.NICHE_KEYWORDS.items():
            if key in niche_lower or niche_lower in key:
                return keywords
        
        return [niche]
    
    def scrape(
        self,
        query: str,
        days_back: int = 7,
        language: str = "en",
        sort_by: str = "relevancy",
        page_size: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Scrape news articles related to the query.
        
        Args:
            query: Topic or niche to search for
            days_back: How many days back to search
            language: Language of articles
            sort_by: Sort method (relevancy, popularity, publishedAt)
            page_size: Number of articles to fetch
            
        Returns:
            List of article data dictionaries
        """
        if not REQUESTS_AVAILABLE:
            logger.warning("Requests not installed. Install with: pip install requests")
            return self._get_mock_data(query)
        
        if not self.api_key:
            logger.warning("NewsAPI key not configured. Using mock data.")
            return self._get_mock_data(query)
        
        # Calculate date range
        from_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
        
        # Build search query with niche keywords
        keywords = self._get_keywords_for_niche(query)
        search_query = " OR ".join([f'"{kw}"' for kw in keywords[:3]])
        
        try:
            response = requests.get(
                f"{self.base_url}/everything",
                params={
                    "q": search_query,
                    "from": from_date,
                    "language": language,
                    "sortBy": sort_by,
                    "pageSize": page_size,
                    "apiKey": self.api_key
                },
                timeout=30
            )
            
            response.raise_for_status()
            data = response.json()
            
            if data.get("status") != "ok":
                logger.error(f"NewsAPI error: {data.get('message', 'Unknown error')}")
                return self._get_mock_data(query)
            
            results = []
            for article in data.get("articles", []):
                # Skip articles without title or content
                if not article.get("title") or article.get("title") == "[Removed]":
                    continue
                
                results.append({
                    "title": article["title"],
                    "summary": article.get("description", "")[:300],
                    "content": article.get("content", "")[:500],
                    "url": article["url"],
                    "source": article.get("source", {}).get("name", "Unknown"),
                    "author": article.get("author", "Unknown"),
                    "published_at": article.get("publishedAt", ""),
                    "image_url": article.get("urlToImage", ""),
                    "engagement": f"From {article.get('source', {}).get('name', 'Unknown')}"
                })
            
            logger.info(f"Fetched {len(results)} news articles for '{query}'")
            return results
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching news: {e}")
            return self._get_mock_data(query)
    
    def _get_mock_data(self, query: str) -> List[Dict[str, Any]]:
        """Return mock data for testing without API credentials."""
        logger.info("Returning mock news data for testing")
        
        return [
            {
                "title": f"New Study Reveals Best Practices for {query}",
                "summary": f"Researchers have discovered new insights about {query} that could change how students prepare...",
                "url": "https://example.com/article1",
                "source": "Education Weekly",
                "author": "Jane Smith",
                "published_at": datetime.now().isoformat(),
                "engagement": "From Education Weekly"
            },
            {
                "title": f"Top Experts Share {query} Tips for 2025",
                "summary": f"Leading educators reveal their top strategies for success in {query}...",
                "url": "https://example.com/article2",
                "source": "Academic Times",
                "author": "John Doe",
                "published_at": datetime.now().isoformat(),
                "engagement": "From Academic Times"
            },
            {
                "title": f"How Technology is Changing {query}",
                "summary": f"AI and new tools are revolutionizing how people approach {query}...",
                "url": "https://example.com/article3",
                "source": "Tech Education",
                "author": "Sarah Johnson",
                "published_at": datetime.now().isoformat(),
                "engagement": "From Tech Education"
            }
        ]
    
    def get_trending_topics(self, niche: str) -> List[str]:
        """
        Extract trending topics from news headlines.
        
        Args:
            niche: The niche to analyze
            
        Returns:
            List of trending topics/themes
        """
        articles = self.scrape(niche, days_back=3, page_size=30)
        
        # Simple topic extraction from titles
        # In a production system, you'd use NLP for better extraction
        topics = []
        for article in articles:
            title = article.get("title", "")
            # Add the title as a potential topic
            if title:
                topics.append(title)
        
        return topics[:10]
