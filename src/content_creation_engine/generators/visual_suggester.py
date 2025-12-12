"""
Visual Suggester Module.
Generates visual suggestions for Instagram Reels scripts.
"""

import json
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path

from config.settings import settings
from ..utils.ai_client import AIClient

logger = logging.getLogger(__name__)


class VisualSuggester:
    """Generates visual suggestions for Instagram Reels."""
    
    def __init__(self, ai_client: Optional[AIClient] = None):
        """
        Initialize the VisualSuggester.
        
        Args:
            ai_client: Optional AI client instance. Creates one if not provided.
        """
        self.ai_client = ai_client or AIClient()
        self.prompt_template = self._load_prompt_template()
    
    def _load_prompt_template(self) -> str:
        """Load the visual suggestions prompt template."""
        prompt_path = settings.prompts_dir / "visual_suggestions.txt"
        try:
            with open(prompt_path, "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            logger.warning(f"Prompt template not found at {prompt_path}, using default")
            return self._get_default_prompt()
    
    def _get_default_prompt(self) -> str:
        """Return a default prompt template."""
        return """Create visual suggestions for an Instagram Reel.

Title: {title}
Hook: {hook}
Main Content: {main_content}
CTA: {cta}
Duration: {duration} seconds
Niche: {niche}

Provide suggestions for:
1. B-Roll footage
2. Text overlays
3. Animations
4. Color scheme
5. Music suggestions
6. Shot list

Return as JSON with b_roll, text_overlays, animations, color_scheme, music_suggestions, and shot_list."""
    
    def suggest_visuals(
        self,
        script: Dict[str, Any],
        idea: Dict[str, Any],
        persona: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate visual suggestions for a script.
        
        Args:
            script: Script dictionary with hook, main_content, cta
            idea: Original content idea
            persona: Persona dictionary with visual preferences
            
        Returns:
            Visual suggestions dictionary
        """
        # Extract persona information
        basic_info = persona.get("basic_info", {})
        style_guide = persona.get("style_guide", {})
        visual_preferences = style_guide.get("visual_preferences", {})
        
        # Build the prompt
        prompt = self.prompt_template.format(
            title=idea.get("title", script.get("idea_title", "")),
            hook=script.get("hook", ""),
            main_content=script.get("main_content", ""),
            cta=script.get("cta", ""),
            duration=script.get("estimated_duration_seconds", 45),
            niche=basic_info.get("niche", settings.content.default_niche),
            visual_preferences=json.dumps(visual_preferences, indent=2)
        )
        
        # Generate visual suggestions using AI
        try:
            response = self.ai_client.generate(
                prompt=prompt,
                system_prompt="You are a creative director for Instagram Reels. Always respond with valid JSON.",
                temperature=0.8  # Higher creativity for visuals
            )
            
            # Parse the response
            visuals = self._parse_visuals_response(response)
            
            # Add metadata
            visuals["script_duration"] = script.get("estimated_duration_seconds", 45)
            visuals["idea_title"] = idea.get("title", "")
            
            logger.info(f"Generated visual suggestions for: {idea.get('title', 'Unknown')}")
            return visuals
            
        except Exception as e:
            logger.error(f"Error generating visual suggestions: {e}")
            return self._get_empty_visuals()
    
    def suggest_visuals_batch(
        self,
        scripts: List[Dict[str, Any]],
        ideas: List[Dict[str, Any]],
        persona: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Generate visual suggestions for multiple scripts.
        
        Args:
            scripts: List of script dictionaries
            ideas: List of content idea dictionaries
            persona: Persona dictionary
            
        Returns:
            List of visual suggestion dictionaries
        """
        visuals_list = []
        
        # Create a mapping of idea_id to idea
        ideas_map = {idea.get("id"): idea for idea in ideas}
        
        for script in scripts:
            idea_id = script.get("idea_id")
            idea = ideas_map.get(idea_id, {"title": script.get("idea_title", "")})
            
            visuals = self.suggest_visuals(script, idea, persona)
            visuals["idea_id"] = idea_id
            visuals_list.append(visuals)
        
        logger.info(f"Generated visual suggestions for {len(visuals_list)} scripts")
        return visuals_list
    
    def _parse_visuals_response(self, response: str) -> Dict[str, Any]:
        """Parse the AI response to extract visual suggestions."""
        try:
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
            
            visuals = json.loads(response)
            return visuals
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse visuals response: {e}")
            logger.debug(f"Raw response: {response}")
            return self._get_empty_visuals()
    
    def _get_empty_visuals(self) -> Dict[str, Any]:
        """Return an empty visuals structure."""
        return {
            "b_roll": [],
            "text_overlays": [],
            "animations": [],
            "color_scheme": {
                "primary": "#000000",
                "secondary": "#FFFFFF",
                "accent": "#FF0000",
                "mood": "Neutral"
            },
            "music_suggestions": {
                "genre": "",
                "tempo": "",
                "mood": "",
                "specific_suggestions": []
            },
            "shot_list": [],
            "overall_style_notes": "",
            "error": "Failed to generate visual suggestions"
        }
    
    def get_b_roll_search_terms(self, visuals: Dict[str, Any]) -> List[str]:
        """
        Extract search terms for finding B-roll footage.
        
        Args:
            visuals: Visual suggestions dictionary
            
        Returns:
            List of search terms for stock footage
        """
        search_terms = []
        
        for b_roll in visuals.get("b_roll", []):
            description = b_roll.get("description", "")
            if description:
                # Extract key terms from description
                search_terms.append(description)
        
        return search_terms
    
    def get_music_search_terms(self, visuals: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get music search parameters.
        
        Args:
            visuals: Visual suggestions dictionary
            
        Returns:
            Dictionary with music search parameters
        """
        music = visuals.get("music_suggestions", {})
        return {
            "genre": music.get("genre", ""),
            "tempo": music.get("tempo", ""),
            "mood": music.get("mood", ""),
            "keywords": music.get("specific_suggestions", [])
        }
    
    def create_storyboard(
        self,
        script: Dict[str, Any],
        visuals: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Create a storyboard combining script and visuals.
        
        Args:
            script: Script dictionary
            visuals: Visual suggestions dictionary
            
        Returns:
            List of storyboard frames
        """
        storyboard = []
        shot_list = visuals.get("shot_list", [])
        text_overlays = visuals.get("text_overlays", [])
        
        # Create frames from shot list
        for shot in shot_list:
            frame = {
                "timestamp": shot.get("timestamp", ""),
                "shot_type": shot.get("shot_type", ""),
                "visual_description": shot.get("description", ""),
                "camera_movement": shot.get("camera_movement", "Static"),
                "text_overlay": None,
                "script_section": ""
            }
            
            # Find matching text overlay
            for overlay in text_overlays:
                if overlay.get("timestamp") == shot.get("timestamp"):
                    frame["text_overlay"] = overlay
                    break
            
            # Determine script section based on timing
            timestamp = shot.get("timestamp", "0-0s")
            if "0-3" in timestamp or "0-5" in timestamp:
                frame["script_section"] = "hook"
            elif "cta" in shot.get("description", "").lower() or "-end" in timestamp:
                frame["script_section"] = "cta"
            else:
                frame["script_section"] = "main_content"
            
            storyboard.append(frame)
        
        return storyboard
