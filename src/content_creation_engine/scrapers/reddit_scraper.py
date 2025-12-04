"""
Reddit scraper using PRAW (Python Reddit API Wrapper).
Scrapes relevant subreddits for trending discussions and content ideas.
"""

from typing import Any, Dict, List, Optional
from pathlib import Path
import logging

try:
    import praw
    PRAW_AVAILABLE = True
except ImportError:
    PRAW_AVAILABLE = False

from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class RedditScraper(BaseScraper):
    """Scraper for Reddit content using PRAW."""
    
    # Default subreddits for different niches
    NICHE_SUBREDDITS = {
        "sat": ["SAT", "SATprep", "ApplyingToCollege", "ACT", "CollegeAdmissions"],
        "sat exam preparation": ["SAT", "SATprep", "ApplyingToCollege", "ACT", "CollegeAdmissions"],
        "fitness": ["Fitness", "bodybuilding", "weightlifting", "GYM", "strength_training"],
        "cooking": ["Cooking", "recipes", "MealPrepSunday", "EatCheapAndHealthy", "foodhacks"],
        "programming": ["learnprogramming", "programming", "webdev", "Python", "coding"],
        "personal finance": ["personalfinance", "FinancialPlanning", "investing", "Frugal"],
    }
    
    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        user_agent: str = "ContentCreationEngine/1.0",
        cache_dir: Optional[Path] = None
    ):
        """
        Initialize Reddit scraper.
        
        Args:
            client_id: Reddit API client ID
            client_secret: Reddit API client secret
            user_agent: User agent string for API requests
            cache_dir: Directory for caching results
        """
        super().__init__(cache_dir)
        
        self.client_id = client_id
        self.client_secret = client_secret
        self.user_agent = user_agent
        self.reddit = None
        
        if PRAW_AVAILABLE and client_id and client_secret:
            try:
                self.reddit = praw.Reddit(
                    client_id=client_id,
                    client_secret=client_secret,
                    user_agent=user_agent
                )
                logger.info("Reddit API client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Reddit client: {e}")
    
    def get_source_name(self) -> str:
        return "reddit"
    
    def _get_subreddits_for_niche(self, niche: str) -> List[str]:
        """Get relevant subreddits for a given niche."""
        niche_lower = niche.lower()
        
        # Check for exact or partial match in predefined niches
        for key, subreddits in self.NICHE_SUBREDDITS.items():
            if key in niche_lower or niche_lower in key:
                return subreddits
        
        # Default: return the niche as a subreddit name
        return [niche.replace(" ", "")]
    
    def scrape(
        self,
        query: str,
        subreddits: Optional[List[str]] = None,
        time_filter: str = "week",
        limit: int = 25,
        sort: str = "hot"
    ) -> List[Dict[str, Any]]:
        """
        Scrape Reddit for content related to the query.
        
        Args:
            query: Niche or topic to search for
            subreddits: List of subreddits to search (auto-detected if None)
            time_filter: Time filter for posts (hour, day, week, month, year, all)
            limit: Maximum posts per subreddit
            sort: Sort method (hot, new, top, rising)
            
        Returns:
            List of post data dictionaries
        """
        if not PRAW_AVAILABLE:
            logger.warning("PRAW not installed. Install with: pip install praw")
            return self._get_mock_data(query)
        
        if not self.reddit:
            logger.warning("Reddit client not initialized. Check API credentials.")
            return self._get_mock_data(query)
        
        # Get subreddits for the niche
        target_subreddits = subreddits or self._get_subreddits_for_niche(query)
        results = []
        
        for subreddit_name in target_subreddits:
            try:
                subreddit = self.reddit.subreddit(subreddit_name)
                
                # Get posts based on sort method
                if sort == "hot":
                    posts = subreddit.hot(limit=limit)
                elif sort == "new":
                    posts = subreddit.new(limit=limit)
                elif sort == "top":
                    posts = subreddit.top(time_filter=time_filter, limit=limit)
                elif sort == "rising":
                    posts = subreddit.rising(limit=limit)
                else:
                    posts = subreddit.hot(limit=limit)
                
                for post in posts:
                    # Skip stickied posts
                    if post.stickied:
                        continue
                    
                    results.append({
                        "title": post.title,
                        "summary": post.selftext[:500] if post.selftext else "",
                        "url": f"https://reddit.com{post.permalink}",
                        "subreddit": subreddit_name,
                        "score": post.score,
                        "num_comments": post.num_comments,
                        "engagement": f"{post.score} upvotes, {post.num_comments} comments",
                        "created_utc": post.created_utc,
                        "is_question": post.title.endswith("?"),
                        "flair": post.link_flair_text
                    })
                    
                logger.info(f"Scraped {len(results)} posts from r/{subreddit_name}")
                
            except Exception as e:
                logger.error(f"Error scraping r/{subreddit_name}: {e}")
                continue
        
        # Sort by engagement (score + comments)
        results.sort(key=lambda x: x["score"] + x["num_comments"], reverse=True)
        
        return results
    
    def _get_mock_data(self, query: str) -> List[Dict[str, Any]]:
        """Return mock data for testing without API credentials."""
        logger.info("Returning mock Reddit data for testing")
        
        return [
            {
                "title": f"Best strategies for {query}?",
                "summary": f"Looking for tips and tricks related to {query}. What has worked for you?",
                "url": "https://reddit.com/r/example/post1",
                "subreddit": "example",
                "score": 150,
                "num_comments": 45,
                "engagement": "150 upvotes, 45 comments",
                "is_question": True,
                "flair": "Discussion"
            },
            {
                "title": f"I improved my {query} results by 30% - here's how",
                "summary": f"After struggling with {query}, I finally found what works...",
                "url": "https://reddit.com/r/example/post2",
                "subreddit": "example",
                "score": 320,
                "num_comments": 78,
                "engagement": "320 upvotes, 78 comments",
                "is_question": False,
                "flair": "Success Story"
            },
            {
                "title": f"Common mistakes people make with {query}",
                "summary": f"I've been helping people with {query} for years, and these are the most common mistakes...",
                "url": "https://reddit.com/r/example/post3",
                "subreddit": "example",
                "score": 540,
                "num_comments": 120,
                "engagement": "540 upvotes, 120 comments",
                "is_question": False,
                "flair": "Tips"
            }
        ]
    
    def get_trending_questions(self, niche: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get trending questions from subreddits - great for content ideas.
        
        Args:
            niche: The niche to search for
            limit: Maximum number of questions to return
            
        Returns:
            List of questions with high engagement
        """
        all_posts = self.scrape(niche, limit=50)
        
        # Filter for questions
        questions = [post for post in all_posts if post.get("is_question", False)]
        
        # Sort by engagement and return top results
        questions.sort(key=lambda x: x["score"] + x["num_comments"], reverse=True)
        
        return questions[:limit]
