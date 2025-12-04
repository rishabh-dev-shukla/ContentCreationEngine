"""
Tests for PersonaManager module.
"""

import pytest
import json
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.content_creation_engine.persona.persona_manager import PersonaManager


class TestPersonaManager:
    """Test cases for PersonaManager."""
    
    def test_init_creates_directory(self, tmp_path):
        """Test that PersonaManager creates the personas directory if it doesn't exist."""
        personas_dir = tmp_path / "new_personas"
        manager = PersonaManager(personas_dir=personas_dir)
        assert personas_dir.exists()
    
    def test_list_personas_empty(self, tmp_path):
        """Test listing personas in empty directory."""
        personas_dir = tmp_path / "personas"
        personas_dir.mkdir()
        manager = PersonaManager(personas_dir=personas_dir)
        assert manager.list_personas() == []
    
    def test_list_personas_with_files(self, temp_personas_dir):
        """Test listing personas with files present."""
        manager = PersonaManager(personas_dir=temp_personas_dir)
        personas = manager.list_personas()
        assert "test_persona" in personas
    
    def test_load_persona_success(self, temp_personas_dir):
        """Test loading an existing persona."""
        manager = PersonaManager(personas_dir=temp_personas_dir)
        persona = manager.load_persona("test_persona")
        
        assert persona["persona_id"] == "test_persona"
        assert "basic_info" in persona
        assert "style_guide" in persona
    
    def test_load_persona_not_found(self, temp_personas_dir):
        """Test loading a non-existent persona raises error."""
        manager = PersonaManager(personas_dir=temp_personas_dir)
        
        with pytest.raises(FileNotFoundError):
            manager.load_persona("nonexistent_persona")
    
    def test_load_persona_caching(self, temp_personas_dir):
        """Test that personas are cached after first load."""
        manager = PersonaManager(personas_dir=temp_personas_dir)
        
        # First load
        persona1 = manager.load_persona("test_persona")
        
        # Second load should use cache
        persona2 = manager.load_persona("test_persona", use_cache=True)
        
        assert persona1 is persona2  # Same object from cache
    
    def test_save_persona(self, tmp_path):
        """Test saving a new persona."""
        personas_dir = tmp_path / "personas"
        personas_dir.mkdir()
        manager = PersonaManager(personas_dir=personas_dir)
        
        new_persona = {
            "persona_id": "new_test_persona",
            "basic_info": {"name": "New Test", "niche": "Testing"},
            "style_guide": {}
        }
        
        saved_id = manager.save_persona(new_persona)
        assert saved_id == "new_test_persona"
        
        # Verify file was created
        assert (personas_dir / "new_test_persona.json").exists()
        
        # Verify content
        loaded = manager.load_persona("new_test_persona")
        assert loaded["basic_info"]["name"] == "New Test"
    
    def test_save_persona_without_id_raises_error(self, tmp_path):
        """Test that saving persona without persona_id raises error."""
        personas_dir = tmp_path / "personas"
        personas_dir.mkdir()
        manager = PersonaManager(personas_dir=personas_dir)
        
        invalid_persona = {"basic_info": {"name": "No ID"}}
        
        with pytest.raises(ValueError):
            manager.save_persona(invalid_persona)
    
    def test_get_style_summary(self, temp_personas_dir, sample_persona):
        """Test getting style summary from persona."""
        # Create persona with full style guide
        with open(temp_personas_dir / "styled_persona.json", "w") as f:
            json.dump(sample_persona, f)
        
        manager = PersonaManager(personas_dir=temp_personas_dir)
        summary = manager.get_style_summary("styled_persona")
        
        # Should contain key elements from the persona
        assert isinstance(summary, str)
        assert "SAT" in summary or "test_persona" in summary.lower()
    
    def test_get_persona_for_generation(self, temp_personas_dir, sample_persona):
        """Test getting persona data formatted for content generation."""
        with open(temp_personas_dir / "full_persona.json", "w") as f:
            json.dump(sample_persona, f)
        
        manager = PersonaManager(personas_dir=temp_personas_dir)
        gen_data = manager.get_persona_for_generation("full_persona")
        
        assert "basic_info" in gen_data
        assert "style_guide" in gen_data
        assert "existing_reels" in gen_data
        assert "_style_summary" in gen_data


class TestPersonaLearning:
    """Test cases for persona learning functionality."""
    
    def test_add_reel_to_persona(self, temp_personas_dir):
        """Test adding a new reel to persona's history."""
        manager = PersonaManager(personas_dir=temp_personas_dir)
        
        # Add a reel using the add_reel method
        manager.add_reel(
            persona_id="test_persona",
            title="New Test Reel",
            script="This is a test script for a new reel.",
            engagement={"views": 1000, "likes": 50, "comments": 5, "shares": 10, "saves": 20}
        )
        
        # Reload and verify
        persona = manager.load_persona("test_persona", use_cache=False)
        assert len(persona.get("existing_reels", [])) >= 1
        
        # Check the added reel
        last_reel = persona["existing_reels"][-1]
        assert last_reel["title"] == "New Test Reel"
    
    def test_create_new_persona(self, tmp_path):
        """Test creating a new persona with create_persona method."""
        personas_dir = tmp_path / "personas"
        personas_dir.mkdir()
        manager = PersonaManager(personas_dir=personas_dir)
        
        persona = manager.create_persona(
            persona_id="new_creator",
            name="Test Creator",
            niche="Python Programming",
            target_audience="Software developers",
            tone="Technical but friendly"
        )
        
        assert persona["persona_id"] == "new_creator"
        assert persona["basic_info"]["niche"] == "Python Programming"
        assert (personas_dir / "new_creator.json").exists()


class TestPersonaValidation:
    """Test persona data structure validation."""
    
    def test_persona_has_required_fields(self, temp_personas_dir):
        """Test that loaded persona has required fields."""
        manager = PersonaManager(personas_dir=temp_personas_dir)
        persona = manager.load_persona("test_persona")
        
        # Check required top-level fields
        assert "persona_id" in persona
        assert "basic_info" in persona
        assert "style_guide" in persona
    
    def test_create_persona_has_all_fields(self, tmp_path):
        """Test that create_persona creates all necessary fields."""
        personas_dir = tmp_path / "personas"
        personas_dir.mkdir()
        manager = PersonaManager(personas_dir=personas_dir)
        
        persona = manager.create_persona(
            persona_id="complete_persona",
            name="Complete Test",
            niche="Testing",
            target_audience="Testers"
        )
        
        # Check all expected fields exist
        assert "persona_id" in persona
        assert "basic_info" in persona
        assert "style_guide" in persona
        assert "existing_reels" in persona
        assert "scripts" in persona
        assert "learned_patterns" in persona
        assert "content_preferences" in persona
