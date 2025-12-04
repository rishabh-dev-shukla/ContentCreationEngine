"""
ContentCreationEngine - Automated Content Creation for Instagram Reels.

A Python application that automates content research, idea generation,
script writing, and visual suggestions for Instagram Reels.
"""

__version__ = "0.1.0"
__author__ = "ContentCreationEngine Team"

from .scrapers import InstagramScraper, NewsScraper, RedditScraper
from .generators import IdeaGenerator, ScriptWriter, VisualSuggester
from .persona import PersonaManager
from .scheduler import DailyWorkflow, ContentPipeline

__all__ = [
    "InstagramScraper",
    "NewsScraper", 
    "RedditScraper",
    "IdeaGenerator",
    "ScriptWriter",
    "VisualSuggester",
    "PersonaManager",
    "DailyWorkflow",
    "ContentPipeline",
]
