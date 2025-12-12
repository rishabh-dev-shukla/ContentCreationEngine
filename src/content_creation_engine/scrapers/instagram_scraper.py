"""
Instagram scraper using Instagram Graph API.
Fetches hashtag insights and trending content for research.
Includes caching to handle rate limits gracefully.
"""

from typing import Any, Dict, List, Optional
from pathlib import Path
from datetime import datetime, timedelta
import logging
import json

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

from .base_scraper import BaseScraper
from config.settings import settings

logger = logging.getLogger(__name__)


class InstagramScraper(BaseScraper):
    """Scraper for Instagram content using Graph API."""
    
    # Common hashtags for different niches
    NICHE_HASHTAGS = {
        "sat": ["satprep", "sattest", "collegeadmissions", "studytips", "testprep", "sat2025"],
        "sat exam preparation": ["satprep", "sattest", "collegeadmissions", "studytips", "testprep"],
        "fitness": ["fitness", "workout", "gym", "fitnessmotivation", "exercise"],
        "cooking": ["cooking", "recipes", "foodie", "homecooking", "cheflife"],
        "programming": ["programming", "coding", "developer", "webdev", "python"],
        "personal finance": ["personalfinance", "investing", "money", "financialfreedom", "budgeting"],
    }
    
    def __init__(
        self,
        access_token: Optional[str] = None,
        business_account_id: Optional[str] = None,
        api_version: str = "v18.0",
        cache_dir: Optional[Path] = None
    ):
        """
        Initialize Instagram scraper.
        
        Args:
            access_token: Instagram Graph API access token
            business_account_id: Instagram Business Account ID
            api_version: Graph API version
            cache_dir: Directory for caching results
        """
        super().__init__(cache_dir)
        
        self.access_token = access_token
        self.business_account_id = business_account_id
        self.api_version = api_version
        self.base_url = f"https://graph.facebook.com/{api_version}"
        
        # Cache settings
        self.cache_max_age_days = 7  # Cache valid for 7 days
    
    def _get_cache_dir(self, persona_id: str) -> Path:
        """Get the cache directory for a persona."""
        cache_dir = settings.data_dir / "research_cache" / persona_id
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir
    
    def _get_cache_file(self, persona_id: str) -> Path:
        """Get the cache file path for Instagram data."""
        return self._get_cache_dir(persona_id) / "instagram_cache.json"
    
    def _load_cached_data(self, persona_id: str) -> Optional[Dict[str, Any]]:
        """
        Load cached Instagram data for a persona.
        
        Args:
            persona_id: The persona identifier
            
        Returns:
            Cached data dict with 'data' and 'timestamp' keys, or None
        """
        cache_file = self._get_cache_file(persona_id)
        
        if not cache_file.exists():
            return None
        
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                cached = json.load(f)
            
            # Check if cache is still valid
            cached_time = datetime.fromisoformat(cached.get("timestamp", "2000-01-01"))
            age = datetime.now() - cached_time
            
            if age > timedelta(days=self.cache_max_age_days):
                logger.info(f"Instagram cache expired ({age.days} days old)")
                return None
            
            logger.info(f"Found Instagram cache from {cached_time.strftime('%Y-%m-%d %H:%M')} ({age.days} days ago)")
            return cached
            
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning(f"Could not load Instagram cache: {e}")
            return None
    
    def _save_cache(self, persona_id: str, data: List[Dict[str, Any]], hashtags: List[str]) -> None:
        """
        Save Instagram data to cache.
        
        Args:
            persona_id: The persona identifier
            data: List of scraped posts
            hashtags: List of hashtags that were searched
        """
        cache_file = self._get_cache_file(persona_id)
        
        try:
            cache_data = {
                "timestamp": datetime.now().isoformat(),
                "hashtags": hashtags,
                "data": data
            }
            
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(cache_data, f, indent=2)
            
            logger.info(f"Cached {len(data)} Instagram posts for persona '{persona_id}'")
            
        except Exception as e:
            logger.warning(f"Could not save Instagram cache: {e}")
    
    def get_source_name(self) -> str:
        return "instagram"
    
    def _get_hashtags_for_niche(self, niche: str) -> List[str]:
        """Get relevant hashtags for a niche."""
        niche_lower = niche.lower()
        
        for key, hashtags in self.NICHE_HASHTAGS.items():
            if key in niche_lower or niche_lower in key:
                return hashtags
        
        # Default: convert niche to hashtag format
        return [niche.lower().replace(" ", "")]
    
    def _make_api_request(self, endpoint: str, params: Dict[str, Any]) -> Optional[Dict]:
        """Make a request to the Instagram Graph API."""
        if not REQUESTS_AVAILABLE:
            return None
        
        params["access_token"] = self.access_token
        
        try:
            response = requests.get(
                f"{self.base_url}/{endpoint}",
                params=params,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            error_msg = str(e)
            # Check for rate limit or specific errors
            if "400" in error_msg:
                logger.warning(f"Instagram API rate limit or invalid request: {e}")
            else:
                logger.error(f"Instagram API error: {e}")
            return None
    
    def search_hashtag(self, hashtag: str) -> Optional[str]:
        """
        Search for a hashtag and get its ID.
        
        Note: Instagram limits hashtag searches to 30 per 7-day rolling period.
        
        Args:
            hashtag: Hashtag to search (without #)
            
        Returns:
            Hashtag ID or None
        """
        if not self.access_token or not self.business_account_id:
            return None
        
        # Normalize hashtag (lowercase, no special chars)
        clean_hashtag = hashtag.lower().replace(" ", "").replace("-", "")
        
        result = self._make_api_request(
            "ig_hashtag_search",
            {
                "user_id": self.business_account_id,
                "q": clean_hashtag
            }
        )
        
        if result and result.get("data"):
            return result["data"][0].get("id")
        
        return None
    
    def get_hashtag_top_media(self, hashtag_id: str, limit: int = 25) -> List[Dict[str, Any]]:
        """
        Get top media for a hashtag.
        
        Args:
            hashtag_id: The hashtag ID from search
            limit: Maximum number of media items
            
        Returns:
            List of media data
        """
        if not self.access_token or not self.business_account_id:
            return []
        
        result = self._make_api_request(
            f"{hashtag_id}/top_media",
            {
                "user_id": self.business_account_id,
                "fields": "id,caption,media_type,permalink,like_count,comments_count,timestamp"
            }
        )
        
        if result and result.get("data"):
            return result["data"][:limit]
        
        return []
    
    def scrape(
        self,
        query: str,
        hashtags: Optional[List[str]] = None,
        limit_per_hashtag: int = 10,
        persona_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Scrape Instagram for content related to the query.
        Falls back to cached data if API fails (rate limiting, etc.)
        
        Args:
            query: Niche or topic to search for
            hashtags: Specific hashtags to search (auto-detected if None)
            limit_per_hashtag: Maximum posts per hashtag
            persona_id: Persona identifier for caching (enables cache fallback)
            
        Returns:
            List of post data dictionaries
        """
        if not REQUESTS_AVAILABLE:
            logger.warning("Requests not installed. Install with: pip install requests")
            return self._get_mock_data(query)
        
        if not self.access_token or not self.business_account_id:
            logger.warning("Instagram API credentials not configured. Using mock data.")
            return self._get_mock_data(query)
        
        target_hashtags = hashtags or self._get_hashtags_for_niche(query)
        results = []
        api_errors = 0
        
        for hashtag in target_hashtags:
            try:
                # Search for hashtag ID
                hashtag_id = self.search_hashtag(hashtag)
                if not hashtag_id:
                    logger.warning(f"Could not find hashtag: {hashtag}")
                    api_errors += 1
                    continue
                
                # Get top media for hashtag
                media_items = self.get_hashtag_top_media(hashtag_id, limit_per_hashtag)
                
                for item in media_items:
                    caption = item.get("caption", "")
                    results.append({
                        "title": caption[:100] + "..." if len(caption) > 100 else caption,
                        "summary": caption[:300] if caption else "",
                        "url": item.get("permalink", ""),
                        "hashtag": hashtag,
                        "media_type": item.get("media_type", ""),
                        "likes": item.get("like_count", 0),
                        "comments": item.get("comments_count", 0),
                        "engagement": f"{item.get('like_count', 0)} likes, {item.get('comments_count', 0)} comments",
                        "timestamp": item.get("timestamp", "")
                    })
                
                logger.info(f"Scraped {len(media_items)} posts for #{hashtag}")
                
            except Exception as e:
                logger.error(f"Error scraping #{hashtag}: {e}")
                api_errors += 1
                continue
        
        # If we got results, save to cache
        if results and persona_id:
            self._save_cache(persona_id, results, target_hashtags)
        
        # If API failed completely, try to use cached data
        if not results and api_errors > 0 and persona_id:
            cached = self._load_cached_data(persona_id)
            if cached and cached.get("data"):
                logger.info(f"Using cached Instagram data ({len(cached['data'])} posts from previous run)")
                return cached["data"]
        
        # Sort by engagement
        results.sort(key=lambda x: x.get("likes", 0) + x.get("comments", 0), reverse=True)
        
        return results
    
    def _get_mock_data(self, query: str) -> List[Dict[str, Any]]:
        """Return mock data for testing without API credentials."""
        logger.info("Returning mock Instagram data for testing")
        
        hashtags = self._get_hashtags_for_niche(query)
        
        return [
            {
                "title": f"🎯 3 Quick Tips for {query} Success!",
                "summary": f"Here are my top 3 tips for {query}: 1. Start early 2. Practice daily 3. Stay consistent! #studytips",
                "url": "https://instagram.com/p/example1",
                "hashtag": hashtags[0] if hashtags else query,
                "media_type": "VIDEO",
                "likes": 1250,
                "comments": 45,
                "engagement": "1250 likes, 45 comments"
            },
            {
                "title": f"POV: You finally understand {query} 😅",
                "summary": f"That moment when it all clicks! Who else has been there? Tag a friend who needs to see this!",
                "url": "https://instagram.com/p/example2",
                "hashtag": hashtags[0] if hashtags else query,
                "media_type": "VIDEO",
                "likes": 2340,
                "comments": 89,
                "engagement": "2340 likes, 89 comments"
            },
            {
                "title": f"Stop making these {query} mistakes! ❌",
                "summary": f"Common mistakes I see students making: 1. Not timing themselves 2. Skipping practice 3. Ignoring weaknesses",
                "url": "https://instagram.com/p/example3",
                "hashtag": hashtags[0] if hashtags else query,
                "media_type": "VIDEO",
                "likes": 890,
                "comments": 34,
                "engagement": "890 likes, 34 comments"
            }
        ]
    
    def get_trending_content_themes(self, niche: str) -> List[str]:
        """
        Extract trending content themes from Instagram posts.
        
        Args:
            niche: The niche to analyze
            
        Returns:
            List of trending themes
        """
        posts = self.scrape(niche, limit_per_hashtag=20)
        
        # Extract themes from captions
        themes = []
        for post in posts:
            caption = post.get("summary", "")
            if caption:
                # Simple extraction - first sentence or line
                first_line = caption.split("\n")[0].split(".")[0]
                if len(first_line) > 10:
                    themes.append(first_line)
        
        return themes[:10]
