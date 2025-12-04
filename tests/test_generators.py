"""
Tests for content generation modules (IdeaGenerator, ScriptWriter, VisualSuggester).
"""

import pytest
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.content_creation_engine.generators.idea_generator import IdeaGenerator
from src.content_creation_engine.generators.script_writer import ScriptWriter
from src.content_creation_engine.generators.visual_suggester import VisualSuggester


class TestIdeaGenerator:
    """Test cases for IdeaGenerator."""
    
    def test_init_with_mock_client(self, mock_ai_client):
        """Test initialization with mock AI client."""
        generator = IdeaGenerator(ai_client=mock_ai_client)
        assert generator.ai_client is mock_ai_client
    
    def test_format_research_data_empty(self, mock_ai_client):
        """Test formatting empty research data."""
        generator = IdeaGenerator(ai_client=mock_ai_client)
        result = generator._format_research_data([])
        assert result == "No data available"
    
    def test_format_research_data_with_items(self, mock_ai_client, sample_research_data):
        """Test formatting research data with items."""
        generator = IdeaGenerator(ai_client=mock_ai_client)
        result = generator._format_research_data(sample_research_data["reddit"])
        
        assert "raised my SAT score" in result
        assert "1." in result  # Should be numbered
    
    def test_parse_ideas_response_valid_json(self, mock_ai_client):
        """Test parsing valid JSON response."""
        generator = IdeaGenerator(ai_client=mock_ai_client)
        
        response = json.dumps([
            {"id": 1, "title": "Test Idea", "concept": "Test concept"}
        ])
        
        ideas = generator._parse_ideas_response(response)
        assert len(ideas) == 1
        assert ideas[0]["title"] == "Test Idea"
    
    def test_parse_ideas_response_with_code_block(self, mock_ai_client):
        """Test parsing response wrapped in markdown code block."""
        generator = IdeaGenerator(ai_client=mock_ai_client)
        
        response = """Here are the ideas:
```json
[{"id": 1, "title": "Test Idea", "concept": "Test concept"}]
```"""
        
        ideas = generator._parse_ideas_response(response)
        assert len(ideas) == 1
    
    def test_generate_ideas_success(
        self, mock_ai_client, sample_persona, sample_research_data, mock_ai_response_ideas
    ):
        """Test successful idea generation."""
        mock_ai_client.generate.return_value = mock_ai_response_ideas
        generator = IdeaGenerator(ai_client=mock_ai_client)
        
        ideas = generator.generate_ideas(
            research_data=sample_research_data,
            persona=sample_persona,
            ideas_count=3
        )
        
        assert len(ideas) == 3
        assert ideas[0]["title"] == "3 Digital SAT Hacks Nobody Talks About"
        mock_ai_client.generate.assert_called_once()
    
    def test_generate_ideas_handles_error(self, mock_ai_client, sample_persona, sample_research_data):
        """Test that generator handles AI client errors gracefully."""
        mock_ai_client.generate.side_effect = Exception("API Error")
        generator = IdeaGenerator(ai_client=mock_ai_client)
        
        ideas = generator.generate_ideas(
            research_data=sample_research_data,
            persona=sample_persona
        )
        
        assert ideas == []  # Should return empty list on error


class TestScriptWriter:
    """Test cases for ScriptWriter."""
    
    def test_init_with_mock_client(self, mock_ai_client):
        """Test initialization with mock AI client."""
        writer = ScriptWriter(ai_client=mock_ai_client)
        assert writer.ai_client is mock_ai_client
    
    def test_write_script_success(
        self, mock_ai_client, sample_content_idea, sample_persona, mock_ai_response_script
    ):
        """Test successful script writing."""
        mock_ai_client.generate.return_value = mock_ai_response_script
        writer = ScriptWriter(ai_client=mock_ai_client)
        
        script = writer.write_script(
            idea=sample_content_idea,
            persona=sample_persona
        )
        
        assert "hook" in script
        assert "main_content" in script
        assert "cta" in script
        assert "full_script" in script
        assert "word_count" in script
    
    def test_write_script_handles_error(self, mock_ai_client, sample_content_idea, sample_persona):
        """Test that script writer handles errors gracefully."""
        mock_ai_client.generate.side_effect = Exception("API Error")
        writer = ScriptWriter(ai_client=mock_ai_client)
        
        script = writer.write_script(
            idea=sample_content_idea,
            persona=sample_persona
        )
        
        # Should return empty script structure
        assert script["hook"] == ""
        assert script["full_script"] == ""
    
    def test_write_scripts_batch(
        self, mock_ai_client, sample_persona, mock_ai_response_script
    ):
        """Test batch script writing."""
        mock_ai_client.generate.return_value = mock_ai_response_script
        writer = ScriptWriter(ai_client=mock_ai_client)
        
        ideas = [
            {"id": 1, "title": "Idea 1", "concept": "Concept 1"},
            {"id": 2, "title": "Idea 2", "concept": "Concept 2"}
        ]
        
        scripts = writer.write_scripts_batch(ideas, sample_persona)
        
        assert len(scripts) == 2
        assert scripts[0]["idea_id"] == 1
        assert scripts[1]["idea_id"] == 2
    
    def test_get_past_scripts_from_persona(self, mock_ai_client, sample_persona):
        """Test extracting past scripts from persona."""
        writer = ScriptWriter(ai_client=mock_ai_client)
        past_scripts = writer._get_past_scripts(sample_persona, limit=3)
        
        # Should contain content from existing_reels or scripts
        assert isinstance(past_scripts, str)


class TestVisualSuggester:
    """Test cases for VisualSuggester."""
    
    def test_init_with_mock_client(self, mock_ai_client):
        """Test initialization with mock AI client."""
        suggester = VisualSuggester(ai_client=mock_ai_client)
        assert suggester.ai_client is mock_ai_client
    
    def test_suggest_visuals_success(
        self, mock_ai_client, sample_script, sample_content_idea, sample_persona, mock_ai_response_visuals
    ):
        """Test successful visual suggestion generation."""
        mock_ai_client.generate.return_value = mock_ai_response_visuals
        suggester = VisualSuggester(ai_client=mock_ai_client)
        
        visuals = suggester.suggest_visuals(
            script=sample_script,
            idea=sample_content_idea,
            persona=sample_persona
        )
        
        assert "b_roll" in visuals
        assert "text_overlays" in visuals
        assert "color_scheme" in visuals
        assert "music_suggestions" in visuals
    
    def test_suggest_visuals_batch(
        self, mock_ai_client, sample_script, sample_persona, mock_ai_response_visuals
    ):
        """Test batch visual suggestion."""
        mock_ai_client.generate.return_value = mock_ai_response_visuals
        suggester = VisualSuggester(ai_client=mock_ai_client)
        
        scripts = [
            {**sample_script, "idea_id": 1, "idea_title": "Script 1"},
            {**sample_script, "idea_id": 2, "idea_title": "Script 2"}
        ]
        
        ideas = [
            {"id": 1, "title": "Script 1", "concept": "Test concept 1"},
            {"id": 2, "title": "Script 2", "concept": "Test concept 2"}
        ]
        
        visuals_list = suggester.suggest_visuals_batch(scripts, ideas, sample_persona)
        
        assert len(visuals_list) == 2
    
    def test_suggest_visuals_handles_error(self, mock_ai_client, sample_script, sample_content_idea, sample_persona):
        """Test that visual suggester handles errors gracefully."""
        mock_ai_client.generate.side_effect = Exception("API Error")
        suggester = VisualSuggester(ai_client=mock_ai_client)
        
        visuals = suggester.suggest_visuals(
            script=sample_script,
            idea=sample_content_idea,
            persona=sample_persona
        )
        
        # Should return empty structure
        assert visuals["b_roll"] == []


class TestGeneratorIntegration:
    """Integration tests for generators working together."""
    
    def test_full_generation_pipeline(
        self, 
        mock_ai_client, 
        sample_persona, 
        sample_research_data,
        mock_ai_response_ideas,
        mock_ai_response_script,
        mock_ai_response_visuals
    ):
        """Test full pipeline: ideas -> scripts -> visuals."""
        # Setup mock responses
        mock_ai_client.generate.side_effect = [
            mock_ai_response_ideas,
            mock_ai_response_script,
            mock_ai_response_script,
            mock_ai_response_script,
            mock_ai_response_visuals,
            mock_ai_response_visuals,
            mock_ai_response_visuals
        ]
        
        # Generate ideas
        idea_gen = IdeaGenerator(ai_client=mock_ai_client)
        ideas = idea_gen.generate_ideas(sample_research_data, sample_persona, ideas_count=3)
        assert len(ideas) == 3
        
        # Write scripts
        script_writer = ScriptWriter(ai_client=mock_ai_client)
        scripts = script_writer.write_scripts_batch(ideas, sample_persona)
        assert len(scripts) == 3
        
        # Generate visuals
        visual_suggester = VisualSuggester(ai_client=mock_ai_client)
        visuals = visual_suggester.suggest_visuals_batch(scripts, ideas, sample_persona)
        assert len(visuals) == 3
