"""
Tests for YouTube Scraper.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from src.content_creation_engine.scrapers.youtube_scraper import YouTubeScraper


class TestYouTubeScraper:
    """Test cases for YouTubeScraper."""
    
    @pytest.fixture
    def scraper(self):
        """Create a YouTubeScraper instance without API key (uses mock data)."""
        scraper = YouTubeScraper(api_key=None)
        return scraper
    
    @pytest.fixture
    def scraper_with_key(self):
        """Create a YouTubeScraper instance with mocked API key."""
        scraper = YouTubeScraper(api_key="test_api_key")
        return scraper
    
    def test_scraper_initialization(self, scraper):
        """Test scraper initializes correctly."""
        assert scraper is not None
        assert scraper.source_name == "youtube"
    
    def test_scraper_initialization_with_key(self, scraper_with_key):
        """Test scraper initializes with API key."""
        assert scraper_with_key.api_key == "test_api_key"
        assert scraper_with_key.base_url == "https://www.googleapis.com/youtube/v3"
    
    def test_get_source_name(self, scraper):
        """Test source name property."""
        assert scraper.get_source_name() == "youtube"
    
    def test_scrape_without_api_key_returns_mock(self, scraper):
        """Test scraping without API key returns mock data."""
        results = scraper.scrape(query="SAT prep", max_results=5)
        
        assert len(results) == 3  # Mock data returns 3 items
        assert all("title" in r for r in results)
        assert all("video_id" in r for r in results)
        assert all("views" in r for r in results)
    
    def test_mock_data_structure(self, scraper):
        """Test mock data has correct structure."""
        results = scraper.scrape(query="SAT prep")
        
        for result in results:
            assert "title" in result
            assert "description" in result
            assert "channel" in result
            assert "video_id" in result
            assert "url" in result
            assert "views" in result
            assert "likes" in result
            assert "comments" in result
    
    def test_get_trending_topics(self, scraper):
        """Test getting trending topics."""
        results = scraper.get_trending_topics("SAT", limit=3)
        
        assert isinstance(results, list)
        # Mock data should return some topics
        for topic in results:
            assert "topic" in topic
            assert "source_video" in topic
    
    def test_get_keywords_for_niche_sat(self, scraper):
        """Test keyword retrieval for SAT niche."""
        keywords = scraper._get_keywords_for_niche("sat")
        
        assert isinstance(keywords, list)
        assert len(keywords) > 0
        assert any("SAT" in k for k in keywords)
    
    def test_get_keywords_for_niche_unknown(self, scraper):
        """Test keyword retrieval for unknown niche."""
        keywords = scraper._get_keywords_for_niche("unknown_niche_xyz")
        
        assert isinstance(keywords, list)
        assert len(keywords) == 1
        assert keywords[0] == "unknown_niche_xyz"
    
    @patch('requests.get')
    def test_scrape_with_api_success(self, mock_get, scraper_with_key):
        """Test successful API scraping."""
        # Mock search response
        mock_search_response = Mock()
        mock_search_response.status_code = 200
        mock_search_response.json.return_value = {
            "items": [
                {
                    "id": {"videoId": "abc123"},
                    "snippet": {
                        "title": "SAT Math Tips",
                        "description": "Best SAT math strategies",
                        "channelTitle": "TestChannel",
                        "publishedAt": "2024-01-15T10:00:00Z",
                        "thumbnails": {"high": {"url": "https://example.com/thumb.jpg"}}
                    }
                }
            ]
        }
        
        # Mock stats response
        mock_stats_response = Mock()
        mock_stats_response.status_code = 200
        mock_stats_response.json.return_value = {
            "items": [
                {
                    "id": "abc123",
                    "statistics": {
                        "viewCount": "150000",
                        "likeCount": "5000",
                        "commentCount": "300"
                    }
                }
            ]
        }
        
        mock_get.side_effect = [mock_search_response, mock_stats_response]
        
        results = scraper_with_key.scrape(query="SAT prep", max_results=1)
        
        # Should have results (may include multiple keywords)
        assert len(results) >= 1
        assert results[0]["video_id"] == "abc123"
        assert results[0]["title"] == "SAT Math Tips"
    
    @patch('requests.get')
    def test_scrape_with_api_error(self, mock_get, scraper_with_key):
        """Test handling of API errors."""
        mock_response = Mock()
        mock_response.status_code = 403
        mock_response.text = "Quota exceeded"
        mock_get.return_value = mock_response
        
        results = scraper_with_key.scrape(query="SAT prep")
        
        # Should return empty on API error
        assert results == []
    
    @patch('requests.get')
    def test_get_video_statistics(self, mock_get, scraper_with_key):
        """Test fetching video statistics."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "items": [
                {"id": "vid1", "statistics": {"viewCount": "1000", "likeCount": "50"}},
                {"id": "vid2", "statistics": {"viewCount": "2000", "likeCount": "100"}}
            ]
        }
        mock_get.return_value = mock_response
        
        stats = scraper_with_key._get_video_statistics(["vid1", "vid2"])
        
        assert "vid1" in stats
        assert "vid2" in stats
        assert stats["vid1"]["viewCount"] == "1000"


class TestYouTubeNicheMapping:
    """Test niche keyword mapping."""
    
    @pytest.fixture
    def scraper(self):
        """Create a YouTubeScraper instance."""
        return YouTubeScraper(api_key=None)
    
    def test_fitness_niche_keywords(self, scraper):
        """Test fitness niche mapping."""
        keywords = scraper._get_keywords_for_niche("fitness")
        
        assert any("workout" in k.lower() for k in keywords)
    
    def test_cooking_niche_keywords(self, scraper):
        """Test cooking niche mapping."""
        keywords = scraper._get_keywords_for_niche("cooking")
        
        assert any("recipe" in k.lower() or "cooking" in k.lower() for k in keywords)
    
    def test_programming_niche_keywords(self, scraper):
        """Test programming niche mapping."""
        keywords = scraper._get_keywords_for_niche("programming")
        
        assert any("coding" in k.lower() or "programming" in k.lower() for k in keywords)
