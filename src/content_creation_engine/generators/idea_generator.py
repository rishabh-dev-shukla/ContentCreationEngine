"""
Idea Generator Module.
Generates content ideas based on research data and persona.
"""

import json
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path
from datetime import datetime, timedelta

from config.settings import settings
from ..utils.ai_client import AIClient

logger = logging.getLogger(__name__)


class IdeaGenerator:
    """Generates content ideas for Instagram Reels based on research data."""
    
    def __init__(self, ai_client: Optional[AIClient] = None):
        """
        Initialize the IdeaGenerator.
        
        Args:
            ai_client: Optional AI client instance. Creates one if not provided.
        """
        self.ai_client = ai_client or AIClient()
        self.prompt_template = self._load_prompt_template()
    
    def _load_prompt_template(self) -> str:
        """Load the idea generation prompt template."""
        prompt_path = settings.prompts_dir / "idea_generation.txt"
        try:
            with open(prompt_path, "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            logger.warning(f"Prompt template not found at {prompt_path}, using default")
            return self._get_default_prompt()
    
    def _get_previous_ideas(self, persona_id: str, days_back: int = 30) -> List[str]:
        """
        Load titles of previously generated ideas to avoid duplicates.
        
        Args:
            persona_id: The persona ID to filter by
            days_back: How many days of history to check
            
        Returns:
            List of previous idea titles
        """
        previous_titles = []
        output_dir = settings.output_dir
        
        if not output_dir.exists():
            return previous_titles
        
        cutoff_date = datetime.now() - timedelta(days=days_back)
        
        # Check persona-specific folder first (new structure)
        persona_output_dir = output_dir / persona_id
        if persona_output_dir.exists():
            for file_path in persona_output_dir.glob("*_content.json"):
                try:
                    # Extract date from filename (format: YYYY-MM-DD_HHMMSS_content.json)
                    date_str = file_path.stem.split("_")[0]
                    file_date = datetime.strptime(date_str, "%Y-%m-%d")
                    
                    if file_date >= cutoff_date:
                        with open(file_path, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            ideas = data.get("content_ideas", [])
                            for idea in ideas:
                                title = idea.get("title", "")
                                if title:
                                    previous_titles.append(title)
                except (ValueError, json.JSONDecodeError, KeyError) as e:
                    logger.debug(f"Could not parse {file_path}: {e}")
                    continue
        
        # Also check old structure for backwards compatibility
        for file_path in output_dir.glob(f"*_{persona_id}_content.json"):
            try:
                date_str = file_path.stem.split("_")[0]
                file_date = datetime.strptime(date_str, "%Y-%m-%d")
                
                if file_date >= cutoff_date:
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        ideas = data.get("content_ideas", [])
                        for idea in ideas:
                            title = idea.get("title", "")
                            if title:
                                previous_titles.append(title)
            except (ValueError, json.JSONDecodeError, KeyError) as e:
                logger.debug(f"Could not parse {file_path}: {e}")
                continue
        
        return previous_titles
    
    def _get_existing_reel_titles(self, persona: Dict[str, Any]) -> List[str]:
        """Extract titles from persona's existing reels."""
        existing_reels = persona.get("existing_reels", [])
        return [reel.get("title", "") for reel in existing_reels if reel.get("title")]
    
    def _get_default_prompt(self) -> str:
        """Return a default prompt template."""
        return """Generate {ideas_count} unique content ideas for Instagram Reels.
        
Niche: {niche}
Target Audience: {target_audience}

Research Data:
- Reddit: {reddit_data}
- News: {news_data}
- Instagram: {instagram_data}

Style Guide: {style_guide}

Return a JSON array with content ideas including title, concept, and engagement potential."""
    
    def generate_ideas(
        self,
        research_data: Dict[str, Any],
        persona: Dict[str, Any],
        ideas_count: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Generate content ideas based on research data and persona.
        
        Args:
            research_data: Dictionary containing scraped data from various sources
            persona: Persona dictionary with style guide and preferences
            ideas_count: Number of ideas to generate (default: 5)
            
        Returns:
            List of content idea dictionaries
        """
        # Extract persona information
        basic_info = persona.get("basic_info", {})
        style_guide = persona.get("style_guide", {})
        persona_id = persona.get("persona_id", "unknown")
        
        # Get previous ideas to avoid duplicates
        previous_titles = self._get_previous_ideas(persona_id, days_back=30)
        existing_reel_titles = self._get_existing_reel_titles(persona)
        all_previous = list(set(previous_titles + existing_reel_titles))
        
        # Format research data for prompt
        reddit_data = self._format_research_data(research_data.get("reddit", []))
        news_data = self._format_research_data(research_data.get("news", []))
        instagram_data = self._format_research_data(research_data.get("instagram", []))
        youtube_data = self._format_research_data(research_data.get("youtube", []))
        serper_data = self._format_research_data(research_data.get("serper", []))
        
        # Build the prompt
        prompt = self.prompt_template.format(
            ideas_count=ideas_count,
            niche=basic_info.get("niche", settings.content.default_niche),
            target_audience=basic_info.get("target_audience", "General audience"),
            reddit_data=reddit_data,
            news_data=news_data,
            instagram_data=instagram_data,
            style_guide=json.dumps(style_guide, indent=2)
        )
        
        # Add previous ideas to avoid duplicates
        if all_previous:
            avoid_section = "\n\n## IMPORTANT: Avoid These Previously Created Ideas\n"
            avoid_section += "Do NOT generate ideas similar to these titles (create completely different concepts):\n"
            for i, title in enumerate(all_previous[-20:], 1):  # Last 20 ideas
                avoid_section += f"- {title}\n"
            prompt += avoid_section
        
        # Add YouTube and Serper data if available
        extra_research = ""
        if youtube_data != "No data available":
            extra_research += f"\n### YouTube Trending Videos:\n{youtube_data}"
        if serper_data != "No data available":
            extra_research += f"\n### Google Search Trends:\n{serper_data}"
        if extra_research:
            prompt = prompt.replace("## Requirements for Each Idea", 
                                   f"{extra_research}\n\n## Requirements for Each Idea")
        
        # Generate ideas using AI
        # Calculate max_tokens based on ideas count (each idea ~400 tokens)
        max_tokens = min(4000, 500 * ideas_count + 500)
        
        try:
            response = self.ai_client.generate(
                prompt=prompt,
                system_prompt="You are an expert social media content strategist. Always respond with valid JSON. Generate FRESH, UNIQUE ideas that are different from any previously created content.",
                temperature=0.9,  # Higher temperature for more creativity and variety
                max_tokens=max_tokens
            )
            
            # Parse the response
            ideas = self._parse_ideas_response(response)
            logger.info(f"Generated {len(ideas)} content ideas (avoided {len(all_previous)} previous ideas)")
            return ideas
            
        except Exception as e:
            logger.error(f"Error generating ideas: {e}")
            return []
    
    def _format_research_data(self, data: List[Dict[str, Any]]) -> str:
        """Format research data for the prompt."""
        if not data:
            return "No data available"
        
        formatted = []
        for i, item in enumerate(data[:10], 1):  # Limit to 10 items
            title = item.get("title", item.get("headline", ""))
            summary = item.get("summary", item.get("description", ""))[:200]
            formatted.append(f"{i}. {title}: {summary}")
        
        return "\n".join(formatted)
    
    def _parse_ideas_response(self, response: str) -> List[Dict[str, Any]]:
        """Parse the AI response to extract content ideas."""
        try:
            # Try to find JSON in the response
            response = response.strip()
            
            # Handle markdown code blocks
            if "```json" in response:
                start = response.find("```json") + 7
                end = response.find("```", start)
                if end == -1:  # No closing ```, response was truncated
                    response = response[start:].strip()
                else:
                    response = response[start:end].strip()
            elif "```" in response:
                start = response.find("```") + 3
                end = response.find("```", start)
                if end == -1:
                    response = response[start:].strip()
                else:
                    response = response[start:end].strip()
            
            # Try to parse as-is first
            try:
                ideas = json.loads(response)
            except json.JSONDecodeError:
                # Try to recover truncated JSON array
                ideas = self._recover_truncated_json(response)
            
            if isinstance(ideas, list):
                return ideas
            elif isinstance(ideas, dict) and "ideas" in ideas:
                return ideas["ideas"]
            else:
                return [ideas]
                
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse ideas response: {e}")
            logger.debug(f"Raw response: {response[:500]}...")
            return []
    
    def _recover_truncated_json(self, response: str) -> List[Dict[str, Any]]:
        """
        Attempt to recover ideas from a truncated JSON response.
        
        Args:
            response: Potentially truncated JSON string
            
        Returns:
            List of successfully parsed ideas
        """
        ideas = []
        
        # Find all complete JSON objects in the array
        # Look for pattern: {"id": ..., ...}
        import re
        
        # Try to find complete idea objects
        depth = 0
        start_idx = None
        
        for i, char in enumerate(response):
            if char == '{':
                if depth == 0:
                    start_idx = i
                depth += 1
            elif char == '}':
                depth -= 1
                if depth == 0 and start_idx is not None:
                    try:
                        obj_str = response[start_idx:i+1]
                        idea = json.loads(obj_str)
                        if isinstance(idea, dict) and ('title' in idea or 'id' in idea):
                            ideas.append(idea)
                    except json.JSONDecodeError:
                        pass
                    start_idx = None
        
        if ideas:
            logger.warning(f"Recovered {len(ideas)} ideas from truncated response")
        
        return ideas
    
    def refine_idea(
        self,
        idea: Dict[str, Any],
        persona: Dict[str, Any],
        feedback: str
    ) -> Dict[str, Any]:
        """
        Refine a content idea based on feedback.
        
        Args:
            idea: The original idea to refine
            persona: Persona dictionary
            feedback: User feedback for refinement
            
        Returns:
            Refined idea dictionary
        """
        prompt = f"""Refine this content idea based on the feedback provided.

Original Idea:
{json.dumps(idea, indent=2)}

Persona Style Guide:
{json.dumps(persona.get('style_guide', {}), indent=2)}

Feedback:
{feedback}

Return the refined idea as a JSON object with the same structure."""
        
        try:
            response = self.ai_client.generate(
                prompt=prompt,
                system_prompt="You are an expert content strategist. Respond with valid JSON only.",
                temperature=0.7
            )
            
            return self._parse_ideas_response(response)[0]
            
        except Exception as e:
            logger.error(f"Error refining idea: {e}")
            return idea
