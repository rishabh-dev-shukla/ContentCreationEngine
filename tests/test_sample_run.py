"""
Sample run tests - validates the complete workflow with sample data.
These tests use mocked AI responses to simulate a full run.
"""

import pytest
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestSampleRun:
    """End-to-end tests using sample data."""
    
    def test_complete_content_generation_flow(
        self,
        sample_persona,
        sample_research_data,
        mock_ai_response_ideas,
        mock_ai_response_script,
        mock_ai_response_visuals,
        tmp_path
    ):
        """
        Test complete flow: Research -> Ideas -> Scripts -> Visuals.
        Uses sample data to validate the entire pipeline.
        """
        from src.content_creation_engine.generators.idea_generator import IdeaGenerator
        from src.content_creation_engine.generators.script_writer import ScriptWriter
        from src.content_creation_engine.generators.visual_suggester import VisualSuggester
        from src.content_creation_engine.scheduler.daily_workflow import ContentOutput
        
        # Create mock AI client
        mock_ai = MagicMock()
        
        # Step 1: Generate Ideas
        mock_ai.generate.return_value = mock_ai_response_ideas
        idea_gen = IdeaGenerator(ai_client=mock_ai)
        ideas = idea_gen.generate_ideas(
            research_data=sample_research_data,
            persona=sample_persona,
            ideas_count=3
        )
        
        assert len(ideas) == 3
        print(f"\n✅ Generated {len(ideas)} content ideas:")
        for idea in ideas:
            print(f"   - {idea['title']}")
        
        # Step 2: Write Scripts
        mock_ai.generate.return_value = mock_ai_response_script
        script_writer = ScriptWriter(ai_client=mock_ai)
        scripts = script_writer.write_scripts_batch(ideas, sample_persona)
        
        assert len(scripts) == 3
        print(f"\n✅ Generated {len(scripts)} scripts:")
        for script in scripts:
            print(f"   - Script for idea {script.get('idea_id')}: {script['word_count']} words")
        
        # Step 3: Generate Visuals
        mock_ai.generate.return_value = mock_ai_response_visuals
        visual_suggester = VisualSuggester(ai_client=mock_ai)
        visuals = visual_suggester.suggest_visuals_batch(scripts, ideas, sample_persona)
        
        assert len(visuals) == 3
        print(f"\n✅ Generated {len(visuals)} visual suggestions")
        
        # Step 4: Create and Save Output
        output = ContentOutput(
            date="2025-12-01",
            persona_id="test_persona",
            niche="SAT Exam Preparation",
            research_data=sample_research_data,
            ideas=ideas,
            scripts=scripts,
            visuals=visuals,
            metadata={
                "test_run": True,
                "ideas_requested": 3,
                "ideas_generated": len(ideas)
            }
        )
        
        output_path = output.save(tmp_path)
        assert output_path.exists()
        print(f"\n✅ Saved output to: {output_path.name}")
        
        # Validate saved content
        with open(output_path, encoding="utf-8") as f:
            saved = json.load(f)
        
        assert saved["persona_id"] == "test_persona"
        assert len(saved["content_ideas"]) == 3
        assert len(saved["scripts"]) == 3
        assert len(saved["visuals"]) == 3
        
        print("\n✅ All validations passed!")
        print(f"\n📄 Sample output structure:")
        print(json.dumps(saved["content_ideas"][0], indent=2))
    
    def test_persona_loading_and_style_extraction(self, temp_personas_dir, sample_persona):
        """Test loading persona and extracting style information."""
        from src.content_creation_engine.persona.persona_manager import PersonaManager
        
        # Save sample persona
        with open(temp_personas_dir / "styled_persona.json", "w") as f:
            json.dump(sample_persona, f)
        
        manager = PersonaManager(personas_dir=temp_personas_dir)
        
        # Load persona
        persona = manager.load_persona("styled_persona")
        assert persona["persona_id"] == "test_persona"
        print(f"\n✅ Loaded persona: {persona['basic_info']['name']}")
        
        # Extract style summary
        summary = manager.get_style_summary("styled_persona")
        assert isinstance(summary, str)
        print(f"   Style summary generated: {len(summary)} chars")
        
        # Check style guide from persona directly
        style = persona.get("style_guide", {})
        assert style["hook_style"] == "Question or shocking statistic"
        print(f"   Hook style: {style['hook_style']}")
        print(f"   Content style: {style['content_style']}")
        print(f"   CTA style: {style['cta_style']}")
    
    def test_research_data_formatting(self, sample_research_data):
        """Test that research data is formatted correctly for prompts."""
        from src.content_creation_engine.generators.idea_generator import IdeaGenerator
        
        mock_ai = MagicMock()
        generator = IdeaGenerator(ai_client=mock_ai)
        
        # Format Reddit data
        reddit_formatted = generator._format_research_data(sample_research_data["reddit"])
        assert "raised my SAT score" in reddit_formatted
        print(f"\n✅ Reddit data formatted ({len(sample_research_data['reddit'])} items)")
        
        # Format News data
        news_formatted = generator._format_research_data(sample_research_data["news"])
        assert "SAT Optional" in news_formatted or "Digital SAT" in news_formatted
        print(f"✅ News data formatted ({len(sample_research_data['news'])} items)")
        
        # Format Instagram data
        instagram_formatted = generator._format_research_data(sample_research_data["instagram"])
        print(f"✅ Instagram data formatted ({len(sample_research_data['instagram'])} items)")
    
    def test_script_structure_validation(self, mock_ai_response_script):
        """Test that generated scripts have the correct structure."""
        script_data = json.loads(mock_ai_response_script)
        
        required_fields = ["hook", "main_content", "cta", "full_script", "word_count"]
        
        for field in required_fields:
            assert field in script_data, f"Missing field: {field}"
        
        print("\n✅ Script structure validation passed")
        print(f"   Hook length: {len(script_data['hook'])} chars")
        print(f"   Main content length: {len(script_data['main_content'])} chars")
        print(f"   Word count: {script_data['word_count']}")
        print(f"   Duration: {script_data['estimated_duration_seconds']} seconds")
    
    def test_visual_suggestions_structure(self, mock_ai_response_visuals):
        """Test that visual suggestions have the correct structure."""
        visuals = json.loads(mock_ai_response_visuals)
        
        required_sections = ["b_roll", "text_overlays", "color_scheme", "music_suggestions"]
        
        for section in required_sections:
            assert section in visuals, f"Missing section: {section}"
        
        print("\n✅ Visual suggestions structure validation passed")
        print(f"   B-roll suggestions: {len(visuals['b_roll'])}")
        print(f"   Text overlays: {len(visuals['text_overlays'])}")
        print(f"   Color scheme: {visuals['color_scheme']['mood']}")


class TestSampleDataValidation:
    """Validate sample data fixtures are correctly structured."""
    
    def test_sample_persona_structure(self, sample_persona):
        """Validate sample persona has all required fields."""
        assert "persona_id" in sample_persona
        assert "basic_info" in sample_persona
        assert "style_guide" in sample_persona
        
        # Validate basic_info
        basic = sample_persona["basic_info"]
        assert "niche" in basic
        assert "target_audience" in basic
        assert "tone" in basic
        
        # Validate style_guide
        style = sample_persona["style_guide"]
        assert "hook_style" in style
        assert "content_style" in style
        assert "cta_style" in style
        
        print("\n✅ Sample persona structure is valid")
    
    def test_sample_research_data_structure(self, sample_research_data):
        """Validate sample research data structure."""
        assert "reddit" in sample_research_data
        assert "news" in sample_research_data
        assert "instagram" in sample_research_data
        
        # Check Reddit data
        for item in sample_research_data["reddit"]:
            assert "title" in item
            assert "summary" in item
        
        # Check News data
        for item in sample_research_data["news"]:
            assert "headline" in item
            assert "description" in item
        
        print("\n✅ Sample research data structure is valid")
    
    def test_sample_content_idea_structure(self, sample_content_idea):
        """Validate sample content idea structure."""
        required_fields = ["id", "title", "concept", "engagement_potential"]
        
        for field in required_fields:
            assert field in sample_content_idea
        
        print("\n✅ Sample content idea structure is valid")
