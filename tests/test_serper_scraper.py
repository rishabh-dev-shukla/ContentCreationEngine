"""
Tests for Serper Scraper.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import requests
from src.content_creation_engine.scrapers.serper_scraper import SerperScraper


class TestSerperScraper:
    """Test cases for SerperScraper."""
    
    @pytest.fixture
    def scraper(self):
        """Create a SerperScraper instance without API key (uses mock data)."""
        return SerperScraper(api_key=None)
    
    @pytest.fixture
    def scraper_with_key(self):
        """Create a SerperScraper instance with API key."""
        return SerperScraper(api_key="test_api_key")
    
    def test_scraper_initialization(self, scraper):
        """Test scraper initializes correctly."""
        assert scraper is not None
        assert scraper.source_name == "serper"
    
    def test_scraper_initialization_with_key(self, scraper_with_key):
        """Test scraper initializes with API key."""
        assert scraper_with_key.api_key == "test_api_key"
        assert scraper_with_key.base_url == "https://google.serper.dev"
    
    def test_get_source_name(self, scraper):
        """Test source name property."""
        assert scraper.get_source_name() == "serper"
    
    def test_scrape_without_api_key_returns_mock(self, scraper):
        """Test scraping without API key returns mock data."""
        results = scraper.scrape(query="SAT prep", num_results=5)
        
        assert len(results) > 0
        assert all("title" in r for r in results)
    
    def test_mock_data_structure(self, scraper):
        """Test mock data has correct structure."""
        results = scraper.scrape(query="SAT prep")
        
        for result in results:
            assert "title" in result
            assert "snippet" in result or result.get("type") == "related"
            assert "type" in result
    
    def test_get_trending_questions(self, scraper):
        """Test getting trending questions."""
        results = scraper.get_trending_questions("SAT", limit=5)
        
        assert isinstance(results, list)
        # All results should be questions
        for q in results:
            assert q.get("type") == "question"
    
    def test_get_related_topics(self, scraper):
        """Test getting related topics."""
        results = scraper.get_related_topics("SAT", limit=5)
        
        assert isinstance(results, list)
        # Results should be strings (topic titles)
        for topic in results:
            assert isinstance(topic, str)
    
    def test_get_competitor_content(self, scraper):
        """Test getting competitor content."""
        results = scraper.get_competitor_content("SAT", limit=5)
        
        assert isinstance(results, list)
        for r in results:
            assert r.get("type") == "organic"
            assert "position" in r
    
    def test_get_queries_for_niche_sat(self, scraper):
        """Test query retrieval for SAT niche."""
        queries = scraper._get_queries_for_niche("sat")
        
        assert isinstance(queries, list)
        assert len(queries) > 0
        assert any("SAT" in q for q in queries)
    
    def test_get_queries_for_niche_unknown(self, scraper):
        """Test query retrieval for unknown niche."""
        queries = scraper._get_queries_for_niche("unknown_niche_xyz")
        
        assert isinstance(queries, list)
        assert len(queries) == 2
        assert "unknown_niche_xyz tips" in queries
    
    @patch('requests.post')
    def test_scrape_with_api_success(self, mock_post, scraper_with_key):
        """Test successful API scraping."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "organic": [
                {
                    "title": "SAT Prep Tips",
                    "link": "https://example.com/sat-tips",
                    "snippet": "Best strategies for SAT",
                    "position": 1
                }
            ],
            "peopleAlsoAsk": [
                {"question": "How to study for SAT?", "snippet": "Answer", "link": "https://example.com"}
            ],
            "relatedSearches": [
                {"query": "SAT practice tests"}
            ]
        }
        mock_post.return_value = mock_response
        
        results = scraper_with_key.scrape(query="SAT prep", num_results=5)
        
        assert len(results) >= 1
        # Check organic result
        organic_results = [r for r in results if r["type"] == "organic"]
        assert len(organic_results) >= 1
        assert organic_results[0]["title"] == "SAT Prep Tips"
    
    @patch('requests.post')
    def test_scrape_with_api_error(self, mock_post, scraper_with_key):
        """Test handling of API errors."""
        mock_response = Mock()
        mock_response.status_code = 403
        mock_response.text = "Forbidden"
        mock_post.return_value = mock_response
        
        results = scraper_with_key.scrape(query="SAT prep")
        
        # Should return empty on API error
        assert results == []
    
    @patch('requests.post')
    def test_search_news(self, mock_post, scraper_with_key):
        """Test news search functionality."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "news": [
                {
                    "title": "SAT Changes Announced",
                    "link": "https://news.example.com/sat",
                    "snippet": "New format coming",
                    "source": "Education Weekly",
                    "date": "2024-01-15"
                }
            ]
        }
        mock_post.return_value = mock_response
        
        results = scraper_with_key.search_news("SAT updates", num_results=5)
        
        assert len(results) == 1
        assert results[0]["title"] == "SAT Changes Announced"
        assert results[0]["type"] == "news"
    
    def test_extract_domain(self, scraper):
        """Test domain extraction from URLs."""
        assert scraper._extract_domain("https://www.example.com/page") == "example.com"
        assert scraper._extract_domain("https://subdomain.example.com/page") == "subdomain.example.com"
        assert scraper._extract_domain("invalid") == "invalid"


class TestSerperNicheMapping:
    """Test niche query mapping."""
    
    @pytest.fixture
    def scraper(self):
        """Create a SerperScraper instance."""
        return SerperScraper(api_key=None)
    
    def test_fitness_niche_queries(self, scraper):
        """Test fitness niche mapping."""
        queries = scraper._get_queries_for_niche("fitness")
        
        assert any("workout" in q.lower() or "fitness" in q.lower() for q in queries)
    
    def test_cooking_niche_queries(self, scraper):
        """Test cooking niche mapping."""
        queries = scraper._get_queries_for_niche("cooking")
        
        assert any("recipe" in q.lower() or "cooking" in q.lower() or "meal" in q.lower() for q in queries)
    
    def test_programming_niche_queries(self, scraper):
        """Test programming niche mapping."""
        queries = scraper._get_queries_for_niche("programming")
        
        assert any("coding" in q.lower() or "programming" in q.lower() for q in queries)


class TestSerperIntegration:
    """Integration-style tests for SerperScraper."""
    
    @pytest.fixture
    def scraper(self):
        """Create a SerperScraper instance."""
        return SerperScraper(api_key=None)
    
    def test_full_research_workflow(self, scraper):
        """Test a complete research workflow using Serper mock data."""
        # Get search results
        search_results = scraper.scrape(query="SAT prep", num_results=10)
        
        # Get trending questions
        questions = scraper.get_trending_questions("SAT", limit=5)
        
        # Get related topics
        related = scraper.get_related_topics("SAT", limit=5)
        
        # Get competitor content
        competitors = scraper.get_competitor_content("SAT", limit=5)
        
        # Verify we got useful data
        assert len(search_results) > 0
        assert isinstance(questions, list)
        assert isinstance(related, list)
        assert isinstance(competitors, list)
