"""
Serper scraper using Serper.dev API.
Fetches Google Search results for trending content and competitor research.
"""

from typing import Any, Dict, List, Optional
from pathlib import Path
import logging

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class SerperScraper(BaseScraper):
    """Scraper for Google Search results using Serper.dev API."""
    
    # Search queries for different niches
    NICHE_QUERIES = {
        "sat": [
            "SAT prep tips 2025",
            "SAT study hacks",
            "best SAT strategies reddit",
            "SAT score improvement tips"
        ],
        "sat exam preparation": [
            "SAT prep tips 2025",
            "digital SAT strategies",
            "SAT math shortcuts",
            "SAT reading comprehension tips"
        ],
        "fitness": [
            "workout tips trending",
            "fitness hacks 2025",
            "gym motivation tips",
            "best exercises for beginners"
        ],
        "cooking": [
            "viral recipes 2025",
            "cooking hacks tiktok",
            "easy meal prep ideas",
            "trending food content"
        ],
        "programming": [
            "coding tips for beginners",
            "programming trends 2025",
            "best coding practices",
            "developer productivity tips"
        ],
        "personal finance": [
            "money saving tips 2025",
            "investing for beginners",
            "budgeting hacks",
            "financial independence tips"
        ],
    }
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        cache_dir: Optional[Path] = None
    ):
        """
        Initialize Serper scraper.
        
        Args:
            api_key: Serper.dev API key
            cache_dir: Directory for caching results
        """
        super().__init__(cache_dir)
        self.api_key = api_key
        self.base_url = "https://google.serper.dev"
    
    def get_source_name(self) -> str:
        return "serper"
    
    def _get_queries_for_niche(self, niche: str) -> List[str]:
        """Get search queries for a niche."""
        niche_lower = niche.lower()
        
        for key, queries in self.NICHE_QUERIES.items():
            if key in niche_lower or niche_lower in key:
                return queries
        
        return [f"{niche} tips", f"{niche} trends 2025"]
    
    def scrape(
        self,
        query: str,
        num_results: int = 10,
        search_type: str = "search"
    ) -> List[Dict[str, Any]]:
        """
        Search Google using Serper API.
        
        Args:
            query: Topic or niche to search for
            num_results: Number of results per query
            search_type: Type of search (search, news, images)
            
        Returns:
            List of search result dictionaries
        """
        if not REQUESTS_AVAILABLE:
            logger.warning("Requests not installed.")
            return self._get_mock_data(query)
        
        if not self.api_key:
            logger.warning("Serper API key not configured. Using mock data.")
            return self._get_mock_data(query)
        
        results = []
        queries = self._get_queries_for_niche(query)
        
        for search_query in queries[:3]:  # Limit to 3 queries to save quota
            try:
                endpoint = f"{self.base_url}/{search_type}"
                
                headers = {
                    "X-API-KEY": self.api_key,
                    "Content-Type": "application/json"
                }
                
                payload = {
                    "q": search_query,
                    "num": num_results
                }
                
                response = requests.post(endpoint, headers=headers, json=payload, timeout=10)
                
                if response.status_code != 200:
                    logger.error(f"Serper API error: {response.status_code} - {response.text}")
                    continue
                
                data = response.json()
                
                # Process organic results
                for item in data.get("organic", []):
                    results.append({
                        "title": item.get("title", ""),
                        "snippet": item.get("snippet", ""),
                        "url": item.get("link", ""),
                        "position": item.get("position", 0),
                        "source": self._extract_domain(item.get("link", "")),
                        "search_query": search_query,
                        "type": "organic"
                    })
                
                # Process "People Also Ask" for content ideas
                for item in data.get("peopleAlsoAsk", []):
                    results.append({
                        "title": item.get("question", ""),
                        "snippet": item.get("snippet", ""),
                        "url": item.get("link", ""),
                        "position": 0,
                        "source": "People Also Ask",
                        "search_query": search_query,
                        "type": "question"
                    })
                
                # Process related searches for trend ideas
                for item in data.get("relatedSearches", []):
                    results.append({
                        "title": item.get("query", ""),
                        "snippet": "",
                        "url": "",
                        "position": 0,
                        "source": "Related Search",
                        "search_query": search_query,
                        "type": "related"
                    })
                
                logger.info(f"Fetched results for '{search_query}'")
                
            except Exception as e:
                logger.error(f"Error fetching Serper data for '{search_query}': {e}")
                continue
        
        return results
    
    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL."""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            return parsed.netloc.replace("www.", "")
        except:
            return url
    
    def get_trending_questions(self, niche: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get trending questions people are asking about a niche.
        Great for content ideas!
        
        Args:
            niche: The content niche
            limit: Maximum questions to return
            
        Returns:
            List of questions with sources
        """
        all_results = self.scrape(niche)
        
        # Filter for questions only
        questions = [r for r in all_results if r["type"] == "question"]
        
        return questions[:limit]
    
    def get_related_topics(self, niche: str, limit: int = 10) -> List[str]:
        """
        Get related search topics for a niche.
        
        Args:
            niche: The content niche
            limit: Maximum topics to return
            
        Returns:
            List of related topic strings
        """
        all_results = self.scrape(niche)
        
        # Filter for related searches
        related = [r["title"] for r in all_results if r["type"] == "related"]
        
        return list(set(related))[:limit]
    
    def get_competitor_content(self, niche: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get top-ranking competitor content for a niche.
        
        Args:
            niche: The content niche
            limit: Maximum results to return
            
        Returns:
            List of competitor content with rankings
        """
        all_results = self.scrape(niche)
        
        # Filter for organic results only
        organic = [r for r in all_results if r["type"] == "organic"]
        
        # Sort by position (lower is better)
        organic.sort(key=lambda x: x["position"])
        
        return organic[:limit]
    
    def search_news(self, query: str, num_results: int = 10) -> List[Dict[str, Any]]:
        """
        Search Google News using Serper.
        
        Args:
            query: Topic to search for
            num_results: Number of results
            
        Returns:
            List of news articles
        """
        if not self.api_key:
            return self._get_mock_news_data(query)
        
        try:
            endpoint = f"{self.base_url}/news"
            
            headers = {
                "X-API-KEY": self.api_key,
                "Content-Type": "application/json"
            }
            
            payload = {
                "q": query,
                "num": num_results
            }
            
            response = requests.post(endpoint, headers=headers, json=payload, timeout=10)
            
            if response.status_code != 200:
                return self._get_mock_news_data(query)
            
            data = response.json()
            
            results = []
            for item in data.get("news", []):
                results.append({
                    "title": item.get("title", ""),
                    "snippet": item.get("snippet", ""),
                    "url": item.get("link", ""),
                    "source": item.get("source", ""),
                    "date": item.get("date", ""),
                    "type": "news"
                })
            
            return results
            
        except Exception as e:
            logger.error(f"Error fetching news: {e}")
            return self._get_mock_news_data(query)
    
    def _get_mock_data(self, query: str) -> List[Dict[str, Any]]:
        """Return mock data for testing without API key."""
        logger.info("Returning mock Serper data for testing")
        
        return [
            {
                "title": f"10 Best {query} Tips for 2025",
                "snippet": f"Discover the most effective strategies for {query}...",
                "url": "https://example.com/tips",
                "position": 1,
                "source": "example.com",
                "search_query": query,
                "type": "organic"
            },
            {
                "title": f"How to improve at {query}?",
                "snippet": f"Many students ask about the best ways to improve...",
                "url": "https://example.com/faq",
                "position": 0,
                "source": "People Also Ask",
                "search_query": query,
                "type": "question"
            },
            {
                "title": f"What are common mistakes in {query}?",
                "snippet": f"Avoid these common pitfalls when preparing...",
                "url": "https://example.com/mistakes",
                "position": 0,
                "source": "People Also Ask",
                "search_query": query,
                "type": "question"
            },
            {
                "title": f"{query} study schedule",
                "snippet": "",
                "url": "",
                "position": 0,
                "source": "Related Search",
                "search_query": query,
                "type": "related"
            },
            {
                "title": f"{query} free resources",
                "snippet": "",
                "url": "",
                "position": 0,
                "source": "Related Search",
                "search_query": query,
                "type": "related"
            }
        ]
    
    def _get_mock_news_data(self, query: str) -> List[Dict[str, Any]]:
        """Return mock news data for testing."""
        return [
            {
                "title": f"Latest Updates on {query} - What You Need to Know",
                "snippet": f"Recent developments in {query} are changing how students prepare...",
                "url": "https://news.example.com/article1",
                "source": "Education News",
                "date": "2 hours ago",
                "type": "news"
            }
        ]
