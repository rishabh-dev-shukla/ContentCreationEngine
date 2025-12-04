"""
Tests for scraper modules (RedditScraper, NewsScraper, InstagramScraper).
These tests use mocked responses to avoid actual API calls.
"""

import pytest
import json
from pathlib import Path
from unittest.mock import MagicMock, patch
from datetime import datetime

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.content_creation_engine.scrapers.reddit_scraper import RedditScraper
from src.content_creation_engine.scrapers.news_scraper import NewsScraper
from src.content_creation_engine.scrapers.instagram_scraper import InstagramScraper


class TestRedditScraper:
    """Test cases for RedditScraper."""
    
    def test_init_without_credentials(self):
        """Test initialization without API credentials."""
        scraper = RedditScraper(client_id=None, client_secret=None)
        assert scraper.reddit is None
    
    def test_get_source_name(self):
        """Test source name getter."""
        scraper = RedditScraper()
        assert scraper.get_source_name() == "reddit"
    
    def test_get_subreddits_for_niche_sat(self):
        """Test getting subreddits for SAT niche."""
        scraper = RedditScraper()
        subreddits = scraper._get_subreddits_for_niche("SAT Exam Preparation")
        
        assert "SAT" in subreddits
        assert "SATprep" in subreddits
    
    def test_get_subreddits_for_unknown_niche(self):
        """Test getting subreddits for unknown niche returns niche as subreddit."""
        scraper = RedditScraper()
        subreddits = scraper._get_subreddits_for_niche("Underwater Basket Weaving")
        
        # Should return normalized niche name
        assert len(subreddits) >= 1
    
    def test_scrape_returns_mock_data_without_credentials(self):
        """Test that scrape returns mock data when no credentials."""
        scraper = RedditScraper(client_id=None, client_secret=None)
        
        results = scraper.scrape("SAT prep")
        
        # Should return mock data
        assert isinstance(results, list)
        assert len(results) > 0
    
    def test_mock_data_structure(self):
        """Test that mock data has expected structure."""
        scraper = RedditScraper(client_id=None, client_secret=None)
        results = scraper.scrape("SAT")
        
        # Check first result has expected keys
        if results:
            result = results[0]
            assert "title" in result
            assert "score" in result
            assert "subreddit" in result


class TestNewsScraper:
    """Test cases for NewsScraper."""
    
    def test_init_without_api_key(self):
        """Test initialization without API key."""
        scraper = NewsScraper(api_key=None)
        assert scraper.api_key is None
    
    def test_get_source_name(self):
        """Test source name getter."""
        scraper = NewsScraper()
        assert scraper.get_source_name() == "news"
    
    def test_get_keywords_for_niche(self):
        """Test getting keywords for a niche."""
        scraper = NewsScraper()
        keywords = scraper._get_keywords_for_niche("SAT Exam Preparation")
        
        assert isinstance(keywords, list)
        assert len(keywords) > 0
    
    def test_scrape_returns_list(self):
        """Test that scrape returns a list."""
        scraper = NewsScraper(api_key=None)
        results = scraper.scrape("SAT prep")
        
        assert isinstance(results, list)
    
    @patch('requests.get')
    def test_scrape_with_mocked_api(self, mock_get):
        """Test scraping with mocked API response."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "ok",
            "articles": [
                {
                    "title": "SAT Test Changes 2025",
                    "description": "Major changes coming to SAT format.",
                    "source": {"name": "Education Weekly"},
                    "publishedAt": "2025-12-01T10:00:00Z",
                    "url": "https://example.com/article"
                }
            ]
        }
        mock_get.return_value = mock_response
        
        scraper = NewsScraper(api_key="test_key")
        results = scraper.scrape("SAT")
        
        assert len(results) >= 1


class TestInstagramScraper:
    """Test cases for InstagramScraper."""
    
    def test_init_without_credentials(self):
        """Test initialization without credentials."""
        scraper = InstagramScraper(access_token=None, business_account_id=None)
        assert scraper.access_token is None
    
    def test_get_source_name(self):
        """Test source name getter."""
        scraper = InstagramScraper()
        assert scraper.get_source_name() == "instagram"
    
    def test_get_hashtags_for_niche(self):
        """Test getting relevant hashtags for a niche."""
        scraper = InstagramScraper()
        hashtags = scraper._get_hashtags_for_niche("SAT Exam Preparation")
        
        assert isinstance(hashtags, list)
        assert len(hashtags) > 0
    
    def test_scrape_returns_list(self):
        """Test that scrape returns a list."""
        scraper = InstagramScraper(access_token=None)
        results = scraper.scrape("SAT prep")
        
        assert isinstance(results, list)


class TestScraperCaching:
    """Test scraper caching functionality."""
    
    def test_cache_directory_creation(self, tmp_path):
        """Test that cache directory is created."""
        cache_dir = tmp_path / "cache"
        scraper = RedditScraper(cache_dir=cache_dir)
        
        # The base class should create the directory
        assert cache_dir.exists()
    
    def test_cache_key_generation(self, tmp_path):
        """Test cache key generation."""
        cache_dir = tmp_path / "cache"
        scraper = RedditScraper(cache_dir=cache_dir)
        
        cache_key = scraper._get_cache_key("SAT prep")
        
        assert "reddit" in cache_key
        assert "SAT" in cache_key or "sat" in cache_key.lower()


class TestScraperIntegration:
    """Integration tests for scrapers working together."""
    
    def test_all_scrapers_return_consistent_format(self):
        """Test that all scrapers return data in consistent format."""
        reddit = RedditScraper()
        news = NewsScraper()
        instagram = InstagramScraper()
        
        # All should return lists
        reddit_data = reddit.scrape("SAT", limit=5)
        news_data = news.scrape("SAT")
        instagram_data = instagram.scrape("SAT")
        
        assert isinstance(reddit_data, list)
        assert isinstance(news_data, list)
        assert isinstance(instagram_data, list)
    
    def test_aggregate_research_data(self, sample_research_data):
        """Test aggregating data from multiple scrapers."""
        # Simulate aggregation
        all_data = {
            "reddit": sample_research_data["reddit"],
            "news": sample_research_data["news"],
            "instagram": sample_research_data["instagram"]
        }
        
        # Verify structure
        assert len(all_data["reddit"]) > 0
        assert len(all_data["news"]) > 0
        assert len(all_data["instagram"]) > 0
        
        # Total content items
        total = sum(len(v) for v in all_data.values())
        assert total > 0
