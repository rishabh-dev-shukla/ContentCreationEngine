"""
Tests for the daily workflow and content pipeline.
"""

import pytest
import json
from pathlib import Path
from datetime import datetime
from unittest.mock import MagicMock, patch

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.content_creation_engine.scheduler.daily_workflow import (
    ContentOutput, ContentPipeline
)


class TestContentOutput:
    """Test cases for ContentOutput dataclass."""
    
    def test_content_output_creation(self):
        """Test creating ContentOutput with basic data."""
        output = ContentOutput(
            date="2025-12-01",
            persona_id="test_persona",
            niche="SAT Exam Preparation"
        )
        
        assert output.date == "2025-12-01"
        assert output.persona_id == "test_persona"
        assert output.niche == "SAT Exam Preparation"
        assert output.ideas == []
        assert output.scripts == []
        assert output.visuals == []
    
    def test_content_output_to_dict(self, sample_research_data):
        """Test converting ContentOutput to dictionary."""
        output = ContentOutput(
            date="2025-12-01",
            persona_id="test_persona",
            niche="SAT Exam Preparation",
            research_data=sample_research_data,
            ideas=[{"id": 1, "title": "Test Idea"}],
            scripts=[{"hook": "Test hook"}],
            visuals=[{"b_roll": []}],
            metadata={"test": True}
        )
        
        result = output.to_dict()
        
        assert result["date"] == "2025-12-01"
        assert result["persona_id"] == "test_persona"
        assert len(result["content_ideas"]) == 1
        assert len(result["scripts"]) == 1
        assert result["metadata"]["test"] == True
    
    def test_content_output_save(self, tmp_path):
        """Test saving ContentOutput to file."""
        output = ContentOutput(
            date="2025-12-01",
            persona_id="test_persona",
            niche="SAT Exam Preparation",
            ideas=[{"id": 1, "title": "Test Idea"}]
        )
        
        file_path = output.save(output_dir=tmp_path)
        
        assert file_path.exists()
        assert "2025-12-01" in file_path.name
        assert "test_persona" in file_path.name
        
        # Verify content
        with open(file_path) as f:
            saved_data = json.load(f)
        assert saved_data["persona_id"] == "test_persona"


class TestContentPipelineUnit:
    """Unit tests for ContentPipeline components."""
    
    def test_content_output_serialization(self, sample_research_data):
        """Test that ContentOutput serializes correctly."""
        output = ContentOutput(
            date="2025-12-01",
            persona_id="test",
            niche="SAT",
            research_data=sample_research_data,
            ideas=[{"id": 1, "title": "Idea"}],
            scripts=[{"hook": "Hook", "full_script": "Full script"}],
            visuals=[{"b_roll": []}]
        )
        
        data = output.to_dict()
        
        # Should be JSON serializable
        json_str = json.dumps(data)
        assert len(json_str) > 0
        
        # Should roundtrip correctly
        parsed = json.loads(json_str)
        assert parsed["persona_id"] == "test"


class TestWorkflowOutput:
    """Test workflow output generation and saving."""
    
    def test_output_file_naming(self, tmp_path):
        """Test that output files are named correctly."""
        output = ContentOutput(
            date="2025-12-01",
            persona_id="sat_guru",
            niche="SAT"
        )
        
        file_path = output.save(tmp_path)
        
        assert file_path.name == "2025-12-01_sat_guru_content.json"
    
    def test_output_contains_all_sections(self, tmp_path, sample_research_data):
        """Test that saved output contains all required sections."""
        output = ContentOutput(
            date="2025-12-01",
            persona_id="test",
            niche="SAT",
            research_data=sample_research_data,
            ideas=[{"id": 1, "title": "Idea 1"}],
            scripts=[{"hook": "Hook 1", "full_script": "Full script 1"}],
            visuals=[{"b_roll": [], "text_overlays": []}],
            metadata={"ideas_requested": 5, "start_time": "2025-12-01T08:00:00"}
        )
        
        file_path = output.save(tmp_path)
        
        with open(file_path) as f:
            saved = json.load(f)
        
        required_keys = ["date", "persona_id", "niche", "research_data", 
                         "content_ideas", "scripts", "visuals", "metadata"]
        
        for key in required_keys:
            assert key in saved, f"Missing key: {key}"
    
    def test_multiple_outputs_same_day(self, tmp_path):
        """Test creating multiple outputs on same day."""
        output1 = ContentOutput(date="2025-12-01", persona_id="persona1", niche="SAT")
        output2 = ContentOutput(date="2025-12-01", persona_id="persona2", niche="ACT")
        
        path1 = output1.save(tmp_path)
        path2 = output2.save(tmp_path)
        
        # Should be different files
        assert path1 != path2
        assert path1.exists()
        assert path2.exists()


class TestSchedulerConfiguration:
    """Test scheduler configuration and setup."""
    
    def test_default_schedule_settings(self):
        """Test default scheduler settings."""
        from config.settings import settings
        
        # Default should be 8:00 AM
        assert settings.scheduler.daily_run_hour == 8
        assert settings.scheduler.daily_run_minute == 0
