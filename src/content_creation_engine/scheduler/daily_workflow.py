"""
Daily Workflow Module.
Orchestrates the full content creation pipeline and scheduling.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field

from config.settings import settings

logger = logging.getLogger(__name__)


@dataclass
class ContentOutput:
    """Represents the output of a daily content generation run."""
    date: str
    persona_id: str
    niche: str
    research_data: Dict[str, Any] = field(default_factory=dict)
    ideas: List[Dict[str, Any]] = field(default_factory=list)
    scripts: List[Dict[str, Any]] = field(default_factory=list)
    visuals: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "date": self.date,
            "persona_id": self.persona_id,
            "niche": self.niche,
            "research_data": self.research_data,
            "content_ideas": self.ideas,
            "scripts": self.scripts,
            "visuals": self.visuals,
            "metadata": self.metadata
        }
    
    def save(self, output_dir: Optional[Path] = None) -> Path:
        """Save output to JSON file."""
        output_dir = output_dir or settings.output_dir
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Add timestamp to ensure unique filenames
        timestamp = datetime.now().strftime("%H%M%S")
        filename = f"{self.date}_{timestamp}_{self.persona_id}_content.json"
        file_path = output_dir / filename
        
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved content output to {file_path}")
        return file_path


class ContentPipeline:
    """
    Content creation pipeline that orchestrates all components.
    """
    
    def __init__(self):
        """Initialize the content pipeline with all components."""
        # Import here to avoid circular imports
        from ..scrapers import InstagramScraper, NewsScraper, RedditScraper, YouTubeScraper, SerperScraper
        from ..generators import IdeaGenerator, ScriptWriter, VisualSuggester
        from ..persona import PersonaManager
        from ..utils.ai_client import AIClient
        
        # Initialize AI client (shared across generators) with settings
        provider = settings.ai.default_provider
        api_key = getattr(settings.ai, f"{provider}_api_key", None)
        model = getattr(settings.ai, f"{provider}_model", None)
        self.ai_client = AIClient(provider=provider, api_key=api_key, model=model)
        
        # Initialize scrapers with API keys from settings
        self.instagram_scraper = InstagramScraper(
            access_token=settings.instagram.access_token,
            business_account_id=settings.instagram.business_account_id
        )
        self.news_scraper = NewsScraper(api_key=settings.news.api_key)
        self.reddit_scraper = RedditScraper()
        self.youtube_scraper = YouTubeScraper(api_key=settings.youtube.api_key)
        self.serper_scraper = SerperScraper(api_key=settings.serper.api_key)
        
        # Initialize generators with shared AI client
        self.idea_generator = IdeaGenerator(ai_client=self.ai_client)
        self.script_writer = ScriptWriter(ai_client=self.ai_client)
        self.visual_suggester = VisualSuggester(ai_client=self.ai_client)
        
        # Initialize persona manager
        self.persona_manager = PersonaManager()
        
        logger.info("Content pipeline initialized")
    
    def run(
        self,
        persona_id: str,
        ideas_count: int = 5,
        skip_scraping: bool = False,
        use_cached_research: bool = False
    ) -> ContentOutput:
        """
        Run the full content creation pipeline.
        
        Args:
            persona_id: ID of the persona to use
            ideas_count: Number of content ideas to generate
            skip_scraping: Skip the scraping phase (use for testing)
            use_cached_research: Use cached research data if available
            
        Returns:
            ContentOutput with all generated content
        """
        start_time = datetime.now()
        date_str = start_time.strftime("%Y-%m-%d")
        
        logger.info(f"Starting content pipeline for persona: {persona_id}")
        
        # Load persona
        persona = self.persona_manager.get_persona_for_generation(persona_id)
        niche = persona.get("basic_info", {}).get("niche", settings.content.default_niche)
        
        # Initialize output
        output = ContentOutput(
            date=date_str,
            persona_id=persona_id,
            niche=niche,
            metadata={
                "start_time": start_time.isoformat(),
                "ideas_requested": ideas_count
            }
        )
        
        # Step 1: Research (scraping)
        if not skip_scraping:
            research_data = self._run_research(niche, persona, use_cached_research)
            output.research_data = research_data
        else:
            logger.info("Skipping scraping phase")
            output.research_data = {"reddit": [], "news": [], "instagram": []}
        
        # Step 2: Generate content ideas
        ideas = self.idea_generator.generate_ideas(
            research_data=output.research_data,
            persona=persona,
            ideas_count=ideas_count
        )
        output.ideas = ideas
        logger.info(f"Generated {len(ideas)} content ideas")
        
        # Step 3: Write scripts for each idea
        scripts = self.script_writer.write_scripts_batch(ideas, persona)
        output.scripts = scripts
        logger.info(f"Written {len(scripts)} scripts")
        
        # Step 4: Generate visual suggestions for each script
        visuals = self.visual_suggester.suggest_visuals_batch(scripts, ideas, persona)
        output.visuals = visuals
        logger.info(f"Generated {len(visuals)} visual suggestions")
        
        # Finalize metadata
        end_time = datetime.now()
        output.metadata.update({
            "end_time": end_time.isoformat(),
            "duration_seconds": (end_time - start_time).total_seconds(),
            "ideas_generated": len(ideas),
            "scripts_generated": len(scripts),
            "visuals_generated": len(visuals)
        })
        
        # Save output
        output_path = output.save()
        output.metadata["output_file"] = str(output_path)
        
        logger.info(f"Pipeline completed in {output.metadata['duration_seconds']:.2f} seconds")
        return output
    
    def _run_research(
        self,
        niche: str,
        persona: Dict[str, Any],
        use_cache: bool = False
    ) -> Dict[str, Any]:
        """
        Run research phase (scraping from all sources).
        
        Args:
            niche: The content niche
            persona: Persona dictionary
            use_cache: Whether to use cached data
            
        Returns:
            Dictionary with research data from all sources
        """
        cache_file = settings.research_cache_dir / f"{datetime.now().strftime('%Y-%m-%d')}_research.json"
        
        # Check for cached data
        if use_cache and cache_file.exists():
            logger.info(f"Using cached research data from {cache_file}")
            with open(cache_file, "r", encoding="utf-8") as f:
                return json.load(f)
        
        research_data = {
            "reddit": [],
            "news": [],
            "instagram": [],
            "youtube": [],
            "serper": []
        }
        
        # Get hashtags and subreddits from persona
        hashtags = persona.get("basic_info", {}).get("hashtags", [])
        
        # Determine subreddits based on niche
        subreddits = self._get_subreddits_for_niche(niche)
        
        # Scrape Reddit (skip if not configured)
        if settings.reddit.client_id and settings.reddit.client_secret:
            logger.info("Scraping Reddit...")
            try:
                for subreddit in subreddits[:3]:  # Limit to 3 subreddits
                    posts = self.reddit_scraper.scrape(subreddit=subreddit, limit=10)
                    research_data["reddit"].extend(posts)
            except Exception as e:
                logger.error(f"Reddit scraping failed: {e}")
        else:
            logger.info("Skipping Reddit (not configured)")
        
        # Scrape News (skip if not configured)
        if settings.news.api_key:
            logger.info("Scraping News...")
            try:
                news_query = self._build_news_query(niche)
                articles = self.news_scraper.scrape(query=news_query, page_size=10)
                research_data["news"] = articles
            except Exception as e:
                logger.error(f"News scraping failed: {e}")
        else:
            logger.info("Skipping News API (not configured)")
        
        # Scrape Instagram (skip if not configured)
        if settings.instagram.access_token and settings.instagram.business_account_id:
            logger.info("Scraping Instagram hashtags...")
            try:
                # Use niche as query, pass hashtags from persona
                posts = self.instagram_scraper.scrape(
                    query=niche,
                    hashtags=[h.replace("#", "") for h in hashtags[:5]],
                    limit_per_hashtag=10
                )
                research_data["instagram"] = posts
            except Exception as e:
                logger.error(f"Instagram scraping failed: {e}")
        else:
            logger.info("Skipping Instagram (not configured)")
        
        # Scrape YouTube for trending videos in niche (skip if not configured)
        if settings.youtube.api_key:
            logger.info("Scraping YouTube...")
            try:
                videos = self.youtube_scraper.scrape(query=niche, max_results=15)
                research_data["youtube"] = videos
                
                # Also get trending topics if available
                trending = self.youtube_scraper.get_trending_topics(niche, limit=5)
                if trending:
                    research_data["youtube_trending_topics"] = trending
            except Exception as e:
                logger.error(f"YouTube scraping failed: {e}")
        else:
            logger.info("Skipping YouTube (not configured)")
        
        # Scrape Serper for Google search trends and news (skip if not configured)
        if settings.serper.api_key:
            logger.info("Scraping Serper (Google Search)...")
            try:
                # Search for trending content
                serper_results = self.serper_scraper.scrape(query=niche, num_results=10)
                research_data["serper"] = serper_results
                
                # Get trending questions related to niche
                trending_questions = self.serper_scraper.get_trending_questions(niche, limit=5)
                if trending_questions:
                    research_data["serper_questions"] = trending_questions
                
                # Get related topics
                related_topics = self.serper_scraper.get_related_topics(niche, limit=5)
                if related_topics:
                    research_data["serper_related"] = related_topics
            except Exception as e:
                logger.error(f"Serper scraping failed: {e}")
        else:
            logger.info("Skipping Serper (not configured)")
        
        # Cache the research data
        settings.research_cache_dir.mkdir(parents=True, exist_ok=True)
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(research_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Research complete: {len(research_data['reddit'])} Reddit, "
                   f"{len(research_data['news'])} News, {len(research_data['instagram'])} Instagram, "
                   f"{len(research_data['youtube'])} YouTube, {len(research_data['serper'])} Serper")
        
        return research_data
    
    def _get_subreddits_for_niche(self, niche: str) -> List[str]:
        """Get relevant subreddits for a niche."""
        niche_lower = niche.lower()
        
        subreddit_mapping = {
            "sat": ["SAT", "ApplyingToCollege", "CollegeAdmissions", "GetStudying"],
            "college": ["ApplyingToCollege", "college", "CollegeAdmissions"],
            "study": ["GetStudying", "studying", "productivity"],
            "exam": ["test_prep", "GetStudying", "college"],
            "finance": ["personalfinance", "investing", "financialindependence"],
            "fitness": ["fitness", "GYM", "bodyweightfitness"],
            "cooking": ["Cooking", "MealPrepSunday", "recipes"],
            "tech": ["technology", "programming", "learnprogramming"],
        }
        
        # Find matching subreddits
        for keyword, subreddits in subreddit_mapping.items():
            if keyword in niche_lower:
                return subreddits
        
        # Default to general subreddits
        return ["popular", "trending"]
    
    def _build_news_query(self, niche: str) -> str:
        """Build a news search query from the niche."""
        # Remove common words and create search query
        niche_words = niche.lower().replace("exam", "").replace("preparation", "").strip()
        return niche_words


class DailyWorkflow:
    """
    Manages the daily scheduled workflow using APScheduler.
    """
    
    def __init__(self):
        """Initialize the daily workflow manager."""
        self.pipeline = ContentPipeline()
        self.scheduler = None
        self._is_running = False
    
    def setup_scheduler(
        self,
        persona_id: str,
        hour: int = 8,
        minute: int = 0,
        timezone: str = "UTC"
    ):
        """
        Set up the daily scheduler.
        
        Args:
            persona_id: ID of the persona to use for content generation
            hour: Hour to run (24-hour format)
            minute: Minute to run
            timezone: Timezone for scheduling
        """
        try:
            from apscheduler.schedulers.background import BackgroundScheduler
            from apscheduler.triggers.cron import CronTrigger
        except ImportError:
            logger.error("APScheduler not installed. Run: pip install apscheduler")
            raise
        
        self.scheduler = BackgroundScheduler(timezone=timezone)
        
        # Add the daily job
        trigger = CronTrigger(hour=hour, minute=minute)
        self.scheduler.add_job(
            func=self._run_daily_job,
            trigger=trigger,
            kwargs={"persona_id": persona_id},
            id="daily_content_generation",
            name="Daily Content Generation",
            replace_existing=True
        )
        
        logger.info(f"Scheduled daily content generation at {hour:02d}:{minute:02d} {timezone}")
    
    def _run_daily_job(self, persona_id: str):
        """Execute the daily content generation job."""
        logger.info(f"Starting daily content generation job for {persona_id}")
        try:
            output = self.pipeline.run(persona_id=persona_id)
            logger.info(f"Daily job completed. Generated {len(output.ideas)} ideas.")
        except Exception as e:
            logger.error(f"Daily job failed: {e}")
    
    def start(self):
        """Start the scheduler."""
        if self.scheduler is None:
            raise RuntimeError("Scheduler not set up. Call setup_scheduler() first.")
        
        self.scheduler.start()
        self._is_running = True
        logger.info("Scheduler started")
    
    def stop(self):
        """Stop the scheduler."""
        if self.scheduler and self._is_running:
            self.scheduler.shutdown()
            self._is_running = False
            logger.info("Scheduler stopped")
    
    def run_now(self, persona_id: str, **kwargs) -> ContentOutput:
        """
        Run the content pipeline immediately (bypass scheduler).
        
        Args:
            persona_id: ID of the persona to use
            **kwargs: Additional arguments for the pipeline
            
        Returns:
            ContentOutput from the pipeline
        """
        logger.info(f"Running content pipeline immediately for {persona_id}")
        return self.pipeline.run(persona_id=persona_id, **kwargs)
    
    def get_next_run_time(self) -> Optional[datetime]:
        """Get the next scheduled run time."""
        if self.scheduler:
            job = self.scheduler.get_job("daily_content_generation")
            if job:
                return job.next_run_time
        return None
    
    def is_running(self) -> bool:
        """Check if the scheduler is running."""
        return self._is_running
