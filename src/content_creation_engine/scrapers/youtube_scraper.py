"""
YouTube scraper using YouTube Data API v3.
Fetches trending videos and content ideas related to the niche.
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


class YouTubeScraper(BaseScraper):
    """Scraper for YouTube videos using YouTube Data API v3."""
    
    # Search keywords for different niches
    NICHE_KEYWORDS = {
        "sat": ["SAT prep tips", "SAT math tricks", "SAT score improvement", "SAT study guide"],
        "sat exam preparation": ["SAT prep tips", "SAT math strategies", "SAT reading tips", "SAT 1500+"],
        "fitness": ["workout tips", "gym motivation", "fitness transformation", "exercise routine"],
        "cooking": ["easy recipes", "cooking hacks", "meal prep", "kitchen tips"],
        "programming": ["coding tutorial", "programming tips", "learn to code", "developer tips"],
        "personal finance": ["money tips", "investing for beginners", "budget tips", "financial freedom"],
    }
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        cache_dir: Optional[Path] = None
    ):
        """
        Initialize YouTube scraper.
        
        Args:
            api_key: YouTube Data API v3 key
            cache_dir: Directory for caching results
        """
        super().__init__(cache_dir)
        self.api_key = api_key
        self.base_url = "https://www.googleapis.com/youtube/v3"
    
    def get_source_name(self) -> str:
        return "youtube"
    
    def _get_keywords_for_niche(self, niche: str) -> List[str]:
        """Get search keywords for a niche."""
        niche_lower = niche.lower()
        
        for key, keywords in self.NICHE_KEYWORDS.items():
            if key in niche_lower or niche_lower in key:
                return keywords
        
        return [niche]
    
    def scrape(
        self,
        query: str,
        max_results: int = 10,
        order: str = "relevance",
        published_after: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search YouTube for videos related to the query.
        
        Args:
            query: Topic or niche to search for
            max_results: Maximum number of videos to fetch
            order: Sort order (relevance, date, rating, viewCount)
            published_after: ISO 8601 date (e.g., "2025-01-01T00:00:00Z")
            
        Returns:
            List of video data dictionaries
        """
        if not REQUESTS_AVAILABLE:
            logger.warning("Requests not installed.")
            return self._get_mock_data(query)
        
        if not self.api_key:
            logger.warning("YouTube API key not configured. Using mock data.")
            return self._get_mock_data(query)
        
        results = []
        keywords = self._get_keywords_for_niche(query)
        
        for keyword in keywords[:2]:  # Limit to 2 keywords to save quota
            try:
                # Search for videos
                search_url = f"{self.base_url}/search"
                params = {
                    "part": "snippet",
                    "q": keyword,
                    "type": "video",
                    "maxResults": max_results,
                    "order": order,
                    "key": self.api_key,
                    "relevanceLanguage": "en"
                }
                
                if published_after:
                    params["publishedAfter"] = published_after
                
                response = requests.get(search_url, params=params, timeout=10)
                
                if response.status_code != 200:
                    logger.error(f"YouTube API error: {response.status_code} - {response.text}")
                    continue
                
                data = response.json()
                
                # Get video IDs for statistics
                video_ids = [item["id"]["videoId"] for item in data.get("items", [])]
                
                # Fetch video statistics
                stats = self._get_video_statistics(video_ids) if video_ids else {}
                
                # Process results
                for item in data.get("items", []):
                    video_id = item["id"]["videoId"]
                    snippet = item["snippet"]
                    video_stats = stats.get(video_id, {})
                    
                    results.append({
                        "title": snippet.get("title", ""),
                        "description": snippet.get("description", "")[:300],
                        "channel": snippet.get("channelTitle", ""),
                        "video_id": video_id,
                        "url": f"https://www.youtube.com/watch?v={video_id}",
                        "thumbnail": snippet.get("thumbnails", {}).get("high", {}).get("url", ""),
                        "published_at": snippet.get("publishedAt", ""),
                        "views": int(video_stats.get("viewCount", 0)),
                        "likes": int(video_stats.get("likeCount", 0)),
                        "comments": int(video_stats.get("commentCount", 0)),
                        "search_keyword": keyword
                    })
                
                logger.info(f"Fetched {len(data.get('items', []))} videos for '{keyword}'")
                
            except Exception as e:
                logger.error(f"Error fetching YouTube data for '{keyword}': {e}")
                continue
        
        # Sort by views
        results.sort(key=lambda x: x["views"], reverse=True)
        
        return results
    
    def _get_video_statistics(self, video_ids: List[str]) -> Dict[str, Dict]:
        """Fetch statistics for multiple videos."""
        if not video_ids:
            return {}
        
        try:
            stats_url = f"{self.base_url}/videos"
            params = {
                "part": "statistics",
                "id": ",".join(video_ids),
                "key": self.api_key
            }
            
            response = requests.get(stats_url, params=params, timeout=10)
            
            if response.status_code != 200:
                return {}
            
            data = response.json()
            
            return {
                item["id"]: item.get("statistics", {})
                for item in data.get("items", [])
            }
            
        except Exception as e:
            logger.error(f"Error fetching video statistics: {e}")
            return {}
    
    def get_trending_topics(self, niche: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get trending video topics in a niche.
        
        Args:
            niche: The content niche
            limit: Maximum topics to return
            
        Returns:
            List of trending topics with engagement data
        """
        videos = self.scrape(niche, max_results=20, order="viewCount")
        
        # Extract unique topics/themes from titles
        topics = []
        seen_themes = set()
        
        for video in videos[:limit]:
            title = video["title"]
            # Simple deduplication by checking key words
            title_words = set(title.lower().split()[:5])
            
            if not title_words & seen_themes:
                topics.append({
                    "topic": title,
                    "source_video": video["url"],
                    "views": video["views"],
                    "channel": video["channel"]
                })
                seen_themes.update(title_words)
        
        return topics
    
    def _get_mock_data(self, query: str) -> List[Dict[str, Any]]:
        """Return mock data for testing without API key."""
        logger.info("Returning mock YouTube data for testing")
        
        return [
            {
                "title": f"How I Scored 1550+ on the SAT - Complete Study Guide",
                "description": f"In this video, I share my complete study strategy for {query}...",
                "channel": "Study Tips Pro",
                "video_id": "mock_video_1",
                "url": "https://www.youtube.com/watch?v=mock_video_1",
                "thumbnail": "",
                "published_at": "2025-11-15T10:00:00Z",
                "views": 250000,
                "likes": 15000,
                "comments": 800,
                "search_keyword": query
            },
            {
                "title": f"SAT Math: 10 Tricks to Save Time",
                "description": "These math shortcuts will help you solve problems faster...",
                "channel": "Math Made Easy",
                "video_id": "mock_video_2",
                "url": "https://www.youtube.com/watch?v=mock_video_2",
                "thumbnail": "",
                "published_at": "2025-11-20T14:00:00Z",
                "views": 180000,
                "likes": 12000,
                "comments": 650,
                "search_keyword": query
            },
            {
                "title": f"From 1200 to 1500: My SAT Journey",
                "description": "How I improved my SAT score by 300 points in 3 months...",
                "channel": "College Prep Journey",
                "video_id": "mock_video_3",
                "url": "https://www.youtube.com/watch?v=mock_video_3",
                "thumbnail": "",
                "published_at": "2025-11-25T08:00:00Z",
                "views": 95000,
                "likes": 8000,
                "comments": 420,
                "search_keyword": query
            }
        ]
