"""
Pytest configuration and fixtures for ContentCreationEngine tests.
"""

import pytest
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


# Sample data fixtures

@pytest.fixture
def sample_persona():
    """Sample persona for testing."""
    return {
        "persona_id": "test_persona",
        "basic_info": {
            "name": "Test SAT Prep",
            "niche": "SAT Exam Preparation",
            "target_audience": "High school students (16-18)",
            "tone": "Friendly, encouraging, slightly humorous",
            "unique_angle": "Quick tips and shortcuts",
            "hashtags": ["#SATprep", "#StudyTips", "#CollegeAdmissions"]
        },
        "style_guide": {
            "hook_style": "Question or shocking statistic",
            "content_style": "Numbered tips, fast-paced",
            "cta_style": "Save and share focused",
            "avoid": ["Complex jargon", "Negative messaging"],
            "visual_preferences": {
                "colors": ["Blue", "White", "Orange"],
                "style": "Clean, modern, educational"
            }
        },
        "existing_reels": [
            {
                "id": "reel_001",
                "title": "3 SAT Math Shortcuts",
                "script": "Did you know most students waste time on SAT math? Here are 3 shortcuts...",
                "engagement": {"views": 15000, "likes": 800, "comments": 45, "shares": 100, "saves": 200}
            }
        ],
        "scripts": ["Hook: Did you know...", "CTA: Save this for later!"],
        "learned_patterns": {
            "auto_generated": False,
            "last_updated": None,
            "avg_script_length": 175,
            "common_topics": ["math shortcuts", "time management"],
            "best_performing_hooks": [],
            "engagement_insights": {
                "best_posting_time": None,
                "avg_engagement_rate": None,
                "top_performing_format": None
            }
        }
    }


@pytest.fixture
def sample_research_data():
    """Sample research data from scrapers."""
    return {
        "reddit": [
            {
                "title": "I raised my SAT score by 200 points - here's how",
                "summary": "After months of prep, I finally cracked the code. The key was practicing with real tests and timing myself.",
                "score": 450,
                "num_comments": 89,
                "subreddit": "SAT"
            },
            {
                "title": "Best free resources for SAT prep?",
                "summary": "Looking for free study materials. Khan Academy has been good but looking for more.",
                "score": 230,
                "num_comments": 56,
                "subreddit": "SATprep"
            },
            {
                "title": "SAT Math Section - Biggest mistakes to avoid",
                "summary": "Tutored 50+ students. Here are the common mistakes I see repeatedly.",
                "score": 380,
                "num_comments": 72,
                "subreddit": "SAT"
            }
        ],
        "news": [
            {
                "headline": "SAT Optional Policies: What 2025 Applicants Need to Know",
                "description": "Many colleges are reinstating SAT requirements for the 2025-2026 admission cycle.",
                "source": "Education Week",
                "published_at": "2025-11-28"
            },
            {
                "headline": "Digital SAT: Tips for the New Format",
                "description": "The transition to digital SAT is complete. Here's what students should expect.",
                "source": "PrepScholar Blog",
                "published_at": "2025-11-25"
            }
        ],
        "instagram": [
            {
                "hashtag": "#SATprep",
                "top_posts": ["Quick math tricks", "Study schedule template", "Score improvement story"],
                "engagement_avg": 5000
            },
            {
                "hashtag": "#StudyTips",
                "top_posts": ["Pomodoro technique explained", "Best study apps 2025"],
                "engagement_avg": 8000
            }
        ]
    }


@pytest.fixture
def sample_content_idea():
    """Sample content idea for script writing tests."""
    return {
        "id": 1,
        "title": "3 Digital SAT Hacks Nobody Talks About",
        "concept": "Cover little-known features of the digital SAT platform that can give students an edge, like the built-in calculator and annotation tools.",
        "why_it_works": "Digital SAT is new, students are anxious about the format",
        "trending_angle": "Connected to recent digital SAT rollout",
        "engagement_potential": "High"
    }


@pytest.fixture
def sample_script():
    """Sample generated script."""
    return {
        "hook": "The digital SAT has secret features that 90% of students don't know about...",
        "main_content": "Feature 1: The built-in Desmos calculator can graph any equation instantly. Feature 2: You can flag questions and come back to them with one click. Feature 3: The annotation tool lets you highlight text as you read. These tools are game-changers if you know how to use them.",
        "cta": "Save this before your test day! Follow for more SAT secrets.",
        "full_script": "The digital SAT has secret features that 90% of students don't know about... Feature 1: The built-in Desmos calculator can graph any equation instantly. Feature 2: You can flag questions and come back to them with one click. Feature 3: The annotation tool lets you highlight text as you read. These tools are game-changers if you know how to use them. Save this before your test day! Follow for more SAT secrets.",
        "word_count": 85,
        "estimated_duration_seconds": 30,
        "speaker_notes": "Speak quickly but clearly. Emphasize 'secret features' and '90%'"
    }


@pytest.fixture
def mock_ai_response_ideas():
    """Mock AI response for idea generation."""
    return json.dumps([
        {
            "id": 1,
            "title": "3 Digital SAT Hacks Nobody Talks About",
            "concept": "Cover hidden features of the digital SAT platform.",
            "why_it_works": "Digital SAT is new and students are curious.",
            "trending_angle": "Connected to digital SAT rollout",
            "engagement_potential": "High",
            "engagement_reasoning": "New format = high curiosity"
        },
        {
            "id": 2,
            "title": "I Scored 1550 Using Only Free Resources",
            "concept": "Showcase free SAT prep resources that actually work.",
            "why_it_works": "Addresses cost concerns of test prep.",
            "trending_angle": "Budget-friendly education trending",
            "engagement_potential": "High",
            "engagement_reasoning": "Free resources always get engagement"
        },
        {
            "id": 3,
            "title": "The 5-Second Rule That Saves Time on SAT Reading",
            "concept": "Quick decision-making technique for reading passages.",
            "why_it_works": "Time management is a major pain point.",
            "trending_angle": "Productivity hacks are trending",
            "engagement_potential": "Medium",
            "engagement_reasoning": "Practical tip with clear benefit"
        }
    ])


@pytest.fixture
def mock_ai_response_script():
    """Mock AI response for script writing."""
    return json.dumps({
        "hook": "Stop wasting time on the SAT reading section...",
        "main_content": "Here's the 5-second rule that changed everything. When you see a question, spend exactly 5 seconds finding the key words. Then scan the passage for those exact words. Most answers are within 2 lines of where you find them. This simple trick helped my students save 10 minutes per section.",
        "cta": "Save this and try it on your next practice test!",
        "full_script": "Stop wasting time on the SAT reading section... Here's the 5-second rule that changed everything. When you see a question, spend exactly 5 seconds finding the key words. Then scan the passage for those exact words. Most answers are within 2 lines of where you find them. This simple trick helped my students save 10 minutes per section. Save this and try it on your next practice test!",
        "word_count": 95,
        "estimated_duration_seconds": 35,
        "speaker_notes": "Use hand gestures when counting to 5"
    })


@pytest.fixture
def mock_ai_response_visuals():
    """Mock AI response for visual suggestions."""
    return json.dumps({
        "b_roll": [
            {"timestamp": "0-3s", "description": "Student looking frustrated at test paper", "purpose": "Hook visual"},
            {"timestamp": "3-15s", "description": "Close-up of highlighter on text", "purpose": "Demonstrate technique"}
        ],
        "text_overlays": [
            {"timestamp": "0-3s", "text": "STOP wasting time! ⏰", "style": "Bold white with red accent", "animation": "Shake effect"},
            {"timestamp": "5-8s", "text": "The 5-Second Rule", "style": "Clean blue on white", "animation": "Fade in"}
        ],
        "animations": [
            {"timestamp": "3-5s", "type": "Transition", "description": "Quick zoom transition"}
        ],
        "color_scheme": {
            "primary": "#1E40AF",
            "secondary": "#FFFFFF",
            "accent": "#F97316",
            "mood": "Energetic and educational"
        },
        "music_suggestions": {
            "genre": "Upbeat lo-fi",
            "tempo": "Medium-fast",
            "mood": "Motivational but not overwhelming",
            "specific_suggestions": ["Study beats", "Focus music"]
        },
        "shot_list": [
            {"shot_number": 1, "timestamp": "0-3s", "shot_type": "Close-up", "description": "Face reaction", "camera_movement": "Static"}
        ],
        "overall_style_notes": "Keep it fast-paced with quick cuts. Use text to reinforce key points."
    })


@pytest.fixture
def temp_personas_dir(tmp_path):
    """Create a temporary personas directory with sample data."""
    personas_dir = tmp_path / "personas"
    personas_dir.mkdir()
    
    # Create sample persona file with complete structure
    sample = {
        "persona_id": "test_persona",
        "basic_info": {
            "name": "Test Persona",
            "niche": "SAT Exam Preparation",
            "target_audience": "High school students"
        },
        "style_guide": {
            "hook_style": "Question",
            "content_style": "Tips format",
            "cta_style": "Save focused",
            "avoid": []
        },
        "existing_reels": [],
        "scripts": [],
        "learned_patterns": {
            "auto_generated": False,
            "last_updated": None,
            "best_performing_hooks": [],
            "avg_script_length": 0,
            "common_topics": [],
            "engagement_insights": {
                "best_posting_time": None,
                "avg_engagement_rate": None,
                "top_performing_format": None
            }
        }
    }
    
    with open(personas_dir / "test_persona.json", "w") as f:
        json.dump(sample, f)
    
    return personas_dir


@pytest.fixture
def mock_ai_client():
    """Mock AI client for testing without API calls."""
    client = MagicMock()
    client.generate.return_value = "Mocked response"
    return client
