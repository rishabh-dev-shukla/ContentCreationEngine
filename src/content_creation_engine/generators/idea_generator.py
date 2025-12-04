"""
Idea Generator Module.
Generates content ideas based on research data and persona.
"""

import json
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path

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
        
        # Format research data for prompt
        reddit_data = self._format_research_data(research_data.get("reddit", []))
        news_data = self._format_research_data(research_data.get("news", []))
        instagram_data = self._format_research_data(research_data.get("instagram", []))
        
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
        
        # Generate ideas using AI
        try:
            response = self.ai_client.generate(
                prompt=prompt,
                system_message="You are an expert social media content strategist. Always respond with valid JSON.",
                temperature=0.8  # Higher creativity for idea generation
            )
            
            # Parse the response
            ideas = self._parse_ideas_response(response)
            logger.info(f"Generated {len(ideas)} content ideas")
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
                response = response[start:end].strip()
            elif "```" in response:
                start = response.find("```") + 3
                end = response.find("```", start)
                response = response[start:end].strip()
            
            ideas = json.loads(response)
            
            if isinstance(ideas, list):
                return ideas
            elif isinstance(ideas, dict) and "ideas" in ideas:
                return ideas["ideas"]
            else:
                return [ideas]
                
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse ideas response: {e}")
            logger.debug(f"Raw response: {response}")
            return []
    
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
                system_message="You are an expert content strategist. Respond with valid JSON only.",
                temperature=0.7
            )
            
            return self._parse_ideas_response(response)[0]
            
        except Exception as e:
            logger.error(f"Error refining idea: {e}")
            return idea
