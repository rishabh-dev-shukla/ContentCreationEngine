"""
Script Writer Module.
Generates scripts for Instagram Reels based on content ideas and persona.
"""

import json
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path

from config.settings import settings
from ..utils.ai_client import AIClient

logger = logging.getLogger(__name__)


class ScriptWriter:
    """Writes engaging scripts for Instagram Reels."""
    
    def __init__(self, ai_client: Optional[AIClient] = None):
        """
        Initialize the ScriptWriter.
        
        Args:
            ai_client: Optional AI client instance. Creates one if not provided.
        """
        self.ai_client = ai_client or AIClient()
        self.prompt_template = self._load_prompt_template()
    
    def _load_prompt_template(self) -> str:
        """Load the script writing prompt template."""
        prompt_path = settings.prompts_dir / "script_writing.txt"
        try:
            with open(prompt_path, "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            logger.warning(f"Prompt template not found at {prompt_path}, using default")
            return self._get_default_prompt()
    
    def _get_default_prompt(self) -> str:
        """Return a default prompt template."""
        return """Write a script for an Instagram Reel.

Title: {title}
Concept: {concept}
Niche: {niche}
Target Audience: {target_audience}
Tone: {tone}
Word Count: {min_words}-{max_words} words

Structure:
1. Hook (attention-grabbing opening)
2. Main Content (value delivery)
3. Call-to-Action (clear CTA)

Return as JSON with hook, main_content, cta, full_script, word_count, and estimated_duration_seconds."""
    
    def write_script(
        self,
        idea: Dict[str, Any],
        persona: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Write a script for a content idea.
        
        Args:
            idea: Content idea dictionary with title and concept
            persona: Persona dictionary with style guide
            
        Returns:
            Script dictionary with hook, main_content, cta, and full_script
        """
        # Extract persona information
        basic_info = persona.get("basic_info", {})
        style_guide = persona.get("style_guide", {})
        
        # Get past scripts for reference
        past_scripts = self._get_past_scripts(persona)
        
        # Build the prompt
        prompt = self.prompt_template.format(
            title=idea.get("title", ""),
            concept=idea.get("concept", ""),
            niche=basic_info.get("niche", settings.content.default_niche),
            target_audience=basic_info.get("target_audience", "General audience"),
            tone=basic_info.get("tone", "Friendly and engaging"),
            hook_style=style_guide.get("hook_style", "Question or bold statement"),
            content_style=style_guide.get("content_style", "Fast-paced, value-packed"),
            cta_style=style_guide.get("cta_style", "Save and share focused"),
            avoid=", ".join(style_guide.get("avoid", [])),
            past_scripts=past_scripts,
            min_words=settings.content.script_min_words,
            max_words=settings.content.script_max_words
        )
        
        # Generate script using AI
        try:
            response = self.ai_client.generate(
                prompt=prompt,
                system_message="You are an expert Instagram Reels scriptwriter. Always respond with valid JSON.",
                temperature=0.7
            )
            
            # Parse the response
            script = self._parse_script_response(response)
            
            # Validate word count
            script = self._validate_script(script)
            
            logger.info(f"Generated script for: {idea.get('title', 'Unknown')}")
            return script
            
        except Exception as e:
            logger.error(f"Error writing script: {e}")
            return self._get_empty_script()
    
    def write_scripts_batch(
        self,
        ideas: List[Dict[str, Any]],
        persona: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Write scripts for multiple content ideas.
        
        Args:
            ideas: List of content idea dictionaries
            persona: Persona dictionary
            
        Returns:
            List of script dictionaries
        """
        scripts = []
        for idea in ideas:
            script = self.write_script(idea, persona)
            script["idea_id"] = idea.get("id")
            script["idea_title"] = idea.get("title")
            scripts.append(script)
        
        logger.info(f"Generated {len(scripts)} scripts")
        return scripts
    
    def _get_past_scripts(self, persona: Dict[str, Any], limit: int = 3) -> str:
        """Get past scripts from persona for reference."""
        existing_reels = persona.get("existing_reels", [])
        scripts = persona.get("scripts", [])
        
        past_examples = []
        
        # Get scripts from existing reels
        for reel in existing_reels[:limit]:
            if "script" in reel:
                past_examples.append(f"Title: {reel.get('title', 'Unknown')}\nScript: {reel['script']}")
        
        # Add any additional script examples
        for script in scripts[:limit]:
            if isinstance(script, str):
                past_examples.append(script)
        
        if not past_examples:
            return "No past scripts available for reference."
        
        return "\n\n---\n\n".join(past_examples)
    
    def _parse_script_response(self, response: str) -> Dict[str, Any]:
        """Parse the AI response to extract the script."""
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
            
            script = json.loads(response)
            return script
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse script response: {e}")
            logger.debug(f"Raw response: {response}")
            return self._get_empty_script()
    
    def _validate_script(self, script: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and fix script if needed."""
        # Ensure all required fields exist
        required_fields = ["hook", "main_content", "cta", "full_script"]
        for field in required_fields:
            if field not in script:
                script[field] = ""
        
        # Build full script if not present
        if not script["full_script"]:
            script["full_script"] = f"{script['hook']}\n\n{script['main_content']}\n\n{script['cta']}"
        
        # Calculate word count if not present
        if "word_count" not in script:
            script["word_count"] = len(script["full_script"].split())
        
        # Estimate duration if not present (roughly 2.5 words per second for speaking)
        if "estimated_duration_seconds" not in script:
            script["estimated_duration_seconds"] = int(script["word_count"] / 2.5)
        
        return script
    
    def _get_empty_script(self) -> Dict[str, Any]:
        """Return an empty script structure."""
        return {
            "hook": "",
            "main_content": "",
            "cta": "",
            "full_script": "",
            "word_count": 0,
            "estimated_duration_seconds": 0,
            "speaker_notes": "",
            "error": "Failed to generate script"
        }
    
    def rewrite_section(
        self,
        script: Dict[str, Any],
        section: str,
        feedback: str,
        persona: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Rewrite a specific section of the script.
        
        Args:
            script: The original script dictionary
            section: Section to rewrite ('hook', 'main_content', or 'cta')
            feedback: User feedback for the rewrite
            persona: Persona dictionary
            
        Returns:
            Updated script dictionary
        """
        if section not in ["hook", "main_content", "cta"]:
            logger.error(f"Invalid section: {section}")
            return script
        
        style_guide = persona.get("style_guide", {})
        
        prompt = f"""Rewrite the {section} of this Instagram Reel script based on the feedback.

Current Script:
Hook: {script.get('hook', '')}
Main Content: {script.get('main_content', '')}
CTA: {script.get('cta', '')}

Section to Rewrite: {section}
Current {section}: {script.get(section, '')}

Feedback: {feedback}

Style Guide:
{json.dumps(style_guide, indent=2)}

Return ONLY the rewritten {section} as plain text, not JSON."""
        
        try:
            response = self.ai_client.generate(
                prompt=prompt,
                system_message="You are an expert scriptwriter. Respond with only the rewritten section.",
                temperature=0.7
            )
            
            script[section] = response.strip()
            script["full_script"] = f"{script['hook']}\n\n{script['main_content']}\n\n{script['cta']}"
            script["word_count"] = len(script["full_script"].split())
            script["estimated_duration_seconds"] = int(script["word_count"] / 2.5)
            
            return script
            
        except Exception as e:
            logger.error(f"Error rewriting section: {e}")
            return script
