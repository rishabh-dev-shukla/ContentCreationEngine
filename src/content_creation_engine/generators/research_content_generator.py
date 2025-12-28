"""
Research Content Generator Module.
Generates content ideas and scripts from selected research data.
"""

import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from config.settings import settings
from ..utils.ai_client import AIClient

logger = logging.getLogger(__name__)


class ResearchContentGenerator:
    """Generates content ideas and scripts from selected research data."""
    
    def __init__(self, ai_client: Optional[AIClient] = None):
        """
        Initialize the ResearchContentGenerator.
        
        Args:
            ai_client: Optional AI client instance. Creates one if not provided.
        """
        if ai_client:
            self.ai_client = ai_client
        else:
            provider = settings.ai.default_provider
            api_key = self._get_api_key_for_provider(provider)
            self.ai_client = AIClient(provider=provider, api_key=api_key)
    
    def _get_api_key_for_provider(self, provider: str) -> Optional[str]:
        """Get the appropriate API key for the given provider."""
        provider_keys = {
            "openai": settings.ai.openai_api_key,
            "deepseek": settings.ai.deepseek_api_key,
            "grok": settings.ai.grok_api_key
        }
        return provider_keys.get(provider.lower())
    
    def generate_content_from_research(
        self,
        selected_research: List[Dict[str, Any]],
        persona: Dict[str, Any],
        ideas_count: int = 5,
        generate_scripts: bool = True,
        extra_instructions: str = ""
    ) -> Dict[str, Any]:
        """
        Generate content ideas and scripts from selected research data.
        
        Args:
            selected_research: List of selected research items with source and content
                Example: [
                    {"source": "youtube", "content": {...}},
                    {"source": "reddit", "content": {...}},
                    {"source": "news", "content": {...}}
                ]
            persona: Persona dictionary with style guide and preferences
            ideas_count: Number of ideas to generate
            generate_scripts: Whether to also generate full scripts
            extra_instructions: Optional extra instructions for content generation
            
        Returns:
            Dictionary containing generated ideas and optionally scripts
        """
        basic_info = persona.get("basic_info", {})
        style_guide = persona.get("style_guide", {})
        
        # Format selected research for the prompt
        research_context = self._format_research_for_prompt(selected_research)
        
        # Build the generation prompt
        prompt = self._build_generation_prompt(
            research_context=research_context,
            niche=basic_info.get("niche", "general"),
            target_audience=basic_info.get("target_audience", "general audience"),
            tone=basic_info.get("tone", "engaging"),
            style_guide=style_guide,
            ideas_count=ideas_count,
            extra_instructions=extra_instructions
        )
        
        logger.info(f"Generating {ideas_count} content ideas from {len(selected_research)} research items")
        
        # Generate ideas
        ideas_response = self.ai_client.generate(
            prompt=prompt,
            system_prompt="You are an expert content creator specializing in viral social media content. You analyze research data to create engaging, unique content ideas that stand out from the competition."
        )
        
        # Parse the response
        ideas = self._parse_ideas_response(ideas_response)
        
        result = {
            "generated_at": datetime.now().isoformat(),
            "persona_id": persona.get("persona_id", "unknown"),
            "source": "research",
            "selected_research_count": len(selected_research),
            "extra_instructions": extra_instructions if extra_instructions else None,
            "content_ideas": ideas,
            "scripts": []
        }
        
        # Generate scripts if requested
        if generate_scripts and ideas:
            scripts = self._generate_scripts_for_ideas(ideas, persona, extra_instructions)
            result["scripts"] = scripts
        
        return result
    
    def _format_research_for_prompt(self, selected_research: List[Dict[str, Any]]) -> str:
        """Format selected research into a structured string for the prompt."""
        formatted_sections = []
        
        # Group research by source
        research_by_source = {}
        for item in selected_research:
            source = item.get("source", "unknown")
            if source not in research_by_source:
                research_by_source[source] = []
            research_by_source[source].append(item.get("content", {}))
        
        # Format each source
        source_formatters = {
            "youtube": self._format_youtube,
            "reddit": self._format_reddit,
            "news": self._format_news,
            "instagram": self._format_instagram,
            "serper": self._format_serper
        }
        
        for source, contents in research_by_source.items():
            formatter = source_formatters.get(source, self._format_generic)
            section_header = source.upper()
            
            formatted_items = []
            for content in contents:
                formatted_items.append(formatter(content))
            
            formatted_sections.append(f"## {section_header} Content\n" + "\n".join(formatted_items))
        
        return "\n\n".join(formatted_sections)
    
    def _format_youtube(self, content: Any) -> str:
        """Format YouTube research item."""
        if isinstance(content, dict):
            title = content.get("title", "Unknown")
            channel = content.get("channel", "Unknown channel")
            views = content.get("views", 0)
            likes = content.get("likes", 0)
            description = content.get("description", "")[:200]
            
            views_str = f"{views:,}" if isinstance(views, int) else str(views)
            likes_str = f"{likes:,}" if isinstance(likes, int) else str(likes)
            
            return f"- **{title}** (by {channel})\n  Views: {views_str} | Likes: {likes_str}\n  Description: {description}..."
        return f"- {content}"
    
    def _format_reddit(self, content: Any) -> str:
        """Format Reddit research item."""
        if isinstance(content, dict):
            title = content.get("title", "Unknown")
            subreddit = content.get("subreddit", "Unknown")
            upvotes = content.get("upvotes", content.get("score", 0))
            comments = content.get("num_comments", content.get("comments", 0))
            summary = content.get("summary", content.get("selftext", ""))[:200]
            
            return f"- **{title}** (r/{subreddit})\n  Upvotes: {upvotes} | Comments: {comments}\n  {summary}..."
        return f"- {content}"
    
    def _format_news(self, content: Any) -> str:
        """Format News research item."""
        if isinstance(content, dict):
            title = content.get("title", content.get("headline", "Unknown"))
            source = content.get("source", "Unknown source")
            summary = content.get("summary", content.get("description", ""))[:200]
            
            return f"- **{title}** ({source})\n  {summary}..."
        return f"- {content}"
    
    def _format_instagram(self, content: Any) -> str:
        """Format Instagram research item."""
        if isinstance(content, dict):
            title = content.get("title", content.get("caption", "Unknown"))[:100]
            likes = content.get("likes", 0)
            comments = content.get("comments", 0)
            views = content.get("views", 0)
            
            likes_str = f"{likes:,}" if isinstance(likes, int) else str(likes)
            
            return f"- **{title}...**\n  Likes: {likes_str} | Comments: {comments} | Views: {views}"
        return f"- {content}"
    
    def _format_serper(self, content: Any) -> str:
        """Format Serper/Google search research item."""
        if isinstance(content, dict):
            title = content.get("title", "Unknown")
            snippet = content.get("snippet", content.get("summary", ""))[:200]
            source = content.get("source", content.get("domain", ""))
            
            return f"- **{title}** ({source})\n  {snippet}..."
        return f"- {content}"
    
    def _format_generic(self, content: Any) -> str:
        """Format generic research item."""
        if isinstance(content, dict):
            title = content.get("title", content.get("headline", "Unknown"))
            summary = content.get("summary", content.get("description", ""))[:200]
            return f"- **{title}**\n  {summary}..."
        return f"- {content}"
    
    def _build_generation_prompt(
        self,
        research_context: str,
        niche: str,
        target_audience: str,
        tone: str,
        style_guide: Dict[str, Any],
        ideas_count: int,
        extra_instructions: str = ""
    ) -> str:
        """Build the prompt for generating content ideas from research."""
        
        style_elements = []
        if style_guide.get("hook_style"):
            style_elements.append(f"Hook Style: {style_guide['hook_style']}")
        if style_guide.get("pacing"):
            style_elements.append(f"Pacing: {style_guide['pacing']}")
        if style_guide.get("signature_elements"):
            style_elements.append(f"Signature Elements: {', '.join(style_guide['signature_elements'])}")
        
        style_section = "\n".join(style_elements) if style_elements else "Engaging and informative"
        
        extra_section = ""
        if extra_instructions:
            extra_section = f"""
## EXTRA INSTRUCTIONS FROM USER
{extra_instructions}

Please incorporate these instructions when generating the content ideas.
"""
        
        prompt = f"""Based on the following research data collected from various platforms, generate {ideas_count} unique content ideas.

# RESEARCH DATA
{research_context}

# CREATOR CONTEXT
- Niche: {niche}
- Target Audience: {target_audience}
- Tone: {tone}
- Style Guide:
{style_section}
{extra_section}
# TASK
Analyze the research data above to identify:
1. Trending topics that are performing well
2. Unique angles not yet covered
3. High-engagement content formats
4. Content gaps and opportunities

Then generate {ideas_count} content ideas that:
- Are inspired by the research but offer a UNIQUE perspective
- Match the creator's niche and style
- Have viral potential based on engagement patterns seen in the research
- Provide clear value to the target audience

# OUTPUT FORMAT
Return your response as a JSON array with exactly {ideas_count} ideas. Each idea should have:
- "title": A compelling, hook-driven title
- "description": 2-3 sentence description of the content
- "format": Suggested content format (e.g., "short-form video", "carousel", "long-form video", "thread")
- "hook": The opening hook/first line
- "key_points": Array of 3-5 main points to cover
- "inspired_by": Which research items inspired this idea
- "viral_potential": "high", "medium", or "low" with brief reasoning
- "source": "research"

Return ONLY the JSON array, no additional text.
"""
        return prompt
    
    def _parse_ideas_response(self, response: str) -> List[Dict[str, Any]]:
        """Parse the AI response to extract content ideas."""
        try:
            # Try to find JSON in the response
            response = response.strip()
            
            # Remove markdown code blocks if present
            if response.startswith("```json"):
                response = response[7:]
            elif response.startswith("```"):
                response = response[3:]
            if response.endswith("```"):
                response = response[:-3]
            
            response = response.strip()
            
            # Parse JSON
            ideas = json.loads(response)
            
            if isinstance(ideas, list):
                # Ensure each idea has the source field
                for idea in ideas:
                    if "source" not in idea:
                        idea["source"] = "research"
                return ideas
            elif isinstance(ideas, dict) and "ideas" in ideas:
                for idea in ideas["ideas"]:
                    if "source" not in idea:
                        idea["source"] = "research"
                return ideas["ideas"]
            
            return []
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse ideas response: {e}")
            logger.debug(f"Response was: {response[:500]}")
            return []
    
    def _generate_scripts_for_ideas(
        self,
        ideas: List[Dict[str, Any]],
        persona: Dict[str, Any],
        extra_instructions: str = ""
    ) -> List[Dict[str, Any]]:
        """Generate full scripts for the content ideas."""
        scripts = []
        basic_info = persona.get("basic_info", {})
        style_guide = persona.get("style_guide", {})
        
        for idea in ideas:
            try:
                script = self._generate_single_script(idea, basic_info, style_guide, extra_instructions)
                if script:
                    scripts.append(script)
            except Exception as e:
                logger.error(f"Failed to generate script for idea '{idea.get('title', 'Unknown')}': {e}")
        
        return scripts
    
    def _generate_single_script(
        self,
        idea: Dict[str, Any],
        basic_info: Dict[str, Any],
        style_guide: Dict[str, Any],
        extra_instructions: str = ""
    ) -> Optional[Dict[str, Any]]:
        """Generate a single script for a content idea."""
        
        extra_section = ""
        if extra_instructions:
            extra_section = f"\n\nADDITIONAL INSTRUCTIONS: {extra_instructions}"
        
        prompt = f"""Create a complete script for the following content idea:

TITLE: {idea.get('title', 'Untitled')}
DESCRIPTION: {idea.get('description', '')}
FORMAT: {idea.get('format', 'short-form video')}
HOOK: {idea.get('hook', '')}
KEY POINTS: {json.dumps(idea.get('key_points', []))}

CREATOR CONTEXT:
- Niche: {basic_info.get('niche', 'general')}
- Target Audience: {basic_info.get('target_audience', 'general audience')}
- Tone: {basic_info.get('tone', 'engaging')}
- Signature Elements: {', '.join(style_guide.get('signature_elements', []))}
{extra_section}

Write a complete, ready-to-record script that:
1. Starts with the hook
2. Covers all key points naturally
3. Maintains the creator's tone and style
4. Includes a strong call-to-action
5. Is optimized for the specified format

Return as JSON with:
- "title": The content title
- "hook": Opening hook (first 3 seconds)
- "full_script": The complete script text (word-for-word what the creator will say)
- "cta": The call-to-action
- "estimated_duration_seconds": Estimated duration in seconds
- "visual_suggestions": Array of visual/B-roll suggestions
- "source": "research"
"""
        
        response = self.ai_client.generate(
            prompt=prompt,
            system_prompt="You are an expert scriptwriter for social media content. You write engaging, viral-worthy scripts that capture attention immediately."
        )
        
        try:
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            elif response.startswith("```"):
                response = response[3:]
            if response.endswith("```"):
                response = response[:-3]
            
            script = json.loads(response.strip())
            script["idea_title"] = idea.get("title", "Untitled")
            script["source"] = "research"
            
            # Normalize field names to match template expectations
            if "script_body" in script and "full_script" not in script:
                script["full_script"] = script.pop("script_body")
            if "call_to_action" in script and "cta" not in script:
                script["cta"] = script.pop("call_to_action")
            if "estimated_duration" in script and "estimated_duration_seconds" not in script:
                script["estimated_duration_seconds"] = script.pop("estimated_duration")
            
            # Calculate word count
            if script.get("full_script"):
                script["word_count"] = len(script["full_script"].split())
            
            return script
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse script response: {e}")
            return None
