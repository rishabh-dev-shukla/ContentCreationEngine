"""
Global settings for ContentCreationEngine.
Loads environment variables and provides configuration access.
"""

import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
CONFIG_DIR = PROJECT_ROOT / "config"
DATA_DIR = PROJECT_ROOT / "data"
PERSONAS_DIR = DATA_DIR / "personas"
OUTPUT_DIR = DATA_DIR / "output"
RESEARCH_CACHE_DIR = DATA_DIR / "research_cache"
PROMPTS_DIR = CONFIG_DIR / "prompts"


@dataclass
class AISettings:
    """AI provider settings."""
    openai_api_key: Optional[str] = field(default_factory=lambda: os.getenv("OPENAI_API_KEY"))
    deepseek_api_key: Optional[str] = field(default_factory=lambda: os.getenv("DEEPSEEK_API_KEY"))
    grok_api_key: Optional[str] = field(default_factory=lambda: os.getenv("GROK_API_KEY"))
    default_provider: str = field(default_factory=lambda: os.getenv("DEFAULT_AI_PROVIDER", "openai"))
    
    # Model configurations
    openai_model: str = "gpt-4"
    deepseek_model: str = "deepseek-chat"
    grok_model: str = "grok-beta"


@dataclass
class InstagramSettings:
    """Instagram Graph API settings."""
    access_token: Optional[str] = field(default_factory=lambda: os.getenv("INSTAGRAM_ACCESS_TOKEN"))
    business_account_id: Optional[str] = field(default_factory=lambda: os.getenv("INSTAGRAM_BUSINESS_ACCOUNT_ID"))
    api_version: str = "v18.0"
    base_url: str = "https://graph.facebook.com"


@dataclass
class RedditSettings:
    """Reddit API settings."""
    client_id: Optional[str] = field(default_factory=lambda: os.getenv("REDDIT_CLIENT_ID"))
    client_secret: Optional[str] = field(default_factory=lambda: os.getenv("REDDIT_CLIENT_SECRET"))
    user_agent: str = field(default_factory=lambda: os.getenv("REDDIT_USER_AGENT", "ContentCreationEngine/1.0"))


@dataclass
class NewsSettings:
    """News API settings."""
    api_key: Optional[str] = field(default_factory=lambda: os.getenv("NEWS_API_KEY"))
    base_url: str = "https://newsapi.org/v2"


@dataclass
class YouTubeSettings:
    """YouTube Data API settings."""
    api_key: Optional[str] = field(default_factory=lambda: os.getenv("YOUTUBE_API_KEY"))
    base_url: str = "https://www.googleapis.com/youtube/v3"


@dataclass
class SerperSettings:
    """Serper.dev API settings."""
    api_key: Optional[str] = field(default_factory=lambda: os.getenv("SERPER_API_KEY"))
    base_url: str = "https://google.serper.dev"


@dataclass
class SchedulerSettings:
    """Scheduler settings."""
    daily_run_hour: int = 8
    daily_run_minute: int = 0
    timezone: str = "UTC"


@dataclass
class ContentSettings:
    """Content generation settings."""
    ideas_per_day: int = 5
    script_min_words: int = 150
    script_max_words: int = 200
    default_niche: str = "SAT Exam Preparation"


@dataclass
class Settings:
    """Main settings container."""
    ai: AISettings = field(default_factory=AISettings)
    instagram: InstagramSettings = field(default_factory=InstagramSettings)
    reddit: RedditSettings = field(default_factory=RedditSettings)
    news: NewsSettings = field(default_factory=NewsSettings)
    youtube: YouTubeSettings = field(default_factory=YouTubeSettings)
    serper: SerperSettings = field(default_factory=SerperSettings)
    scheduler: SchedulerSettings = field(default_factory=SchedulerSettings)
    content: ContentSettings = field(default_factory=ContentSettings)
    
    # Paths
    project_root: Path = PROJECT_ROOT
    data_dir: Path = DATA_DIR
    personas_dir: Path = PERSONAS_DIR
    output_dir: Path = OUTPUT_DIR
    research_cache_dir: Path = RESEARCH_CACHE_DIR
    prompts_dir: Path = PROMPTS_DIR
    
    def ensure_directories(self):
        """Create necessary directories if they don't exist."""
        for dir_path in [self.data_dir, self.personas_dir, self.output_dir, 
                         self.research_cache_dir, self.prompts_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)


# Global settings instance
settings = Settings()
