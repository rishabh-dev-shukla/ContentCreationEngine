"""
Insights Content Generator Module.
Generates content ideas and scripts from previously analyzed insights.
"""

import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from config.settings import settings
from ..utils.ai_client import AIClient

logger = logging.getLogger(__name__)


class InsightsContentGenerator:
    """Generates content ideas and scripts from selected insights."""
    
    def __init__(self, ai_client: Optional[AIClient] = None):
        """
        Initialize the InsightsContentGenerator.
        
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
    
    def generate_content_from_insights(
        self,
        selected_insights: List[Dict[str, Any]],
        persona: Dict[str, Any],
        ideas_count: int = 5,
        generate_scripts: bool = True
    ) -> Dict[str, Any]:
        """
        Generate content ideas and scripts from selected insights.
        
        Args:
            selected_insights: List of selected insight items with type and content
                Example: [
                    {"type": "pain_point", "content": {...}},
                    {"type": "trend", "content": {...}},
                    {"type": "content_gap", "content": {...}}
                ]
            persona: Persona dictionary with style guide and preferences
            ideas_count: Number of ideas to generate
            generate_scripts: Whether to also generate full scripts
            
        Returns:
            Dictionary containing generated ideas and optionally scripts
        """
        basic_info = persona.get("basic_info", {})
        style_guide = persona.get("style_guide", {})
        
        # Format selected insights for the prompt
        insights_context = self._format_insights_for_prompt(selected_insights)
        
        # Build the generation prompt
        prompt = self._build_generation_prompt(
            insights_context=insights_context,
            niche=basic_info.get("niche", "general"),
            target_audience=basic_info.get("target_audience", "general audience"),
            tone=basic_info.get("tone", "engaging"),
            style_guide=style_guide,
            ideas_count=ideas_count
        )
        
        logger.info(f"Generating {ideas_count} content ideas from {len(selected_insights)} selected insights")
        
        # Generate ideas
        ideas_response = self.ai_client.generate(
            prompt=prompt,
            system_prompt="You are an expert content creator specializing in viral social media content. You create engaging, actionable content ideas based on research insights."
        )
        
        # Parse the response
        ideas = self._parse_ideas_response(ideas_response)
        
        result = {
            "generated_at": datetime.now().isoformat(),
            "persona_id": persona.get("persona_id", "unknown"),
            "source": "insights",
            "selected_insights_count": len(selected_insights),
            "content_ideas": ideas,
            "scripts": []
        }
        
        # Generate scripts if requested
        if generate_scripts and ideas:
            scripts = self._generate_scripts_for_ideas(ideas, persona)
            result["scripts"] = scripts
        
        return result
    
    def _format_insights_for_prompt(self, selected_insights: List[Dict[str, Any]]) -> str:
        """Format selected insights into a structured string for the prompt."""
        formatted_sections = []
        
        # Group insights by type
        insights_by_type = {}
        for insight in selected_insights:
            insight_type = insight.get("type", "unknown")
            if insight_type not in insights_by_type:
                insights_by_type[insight_type] = []
            insights_by_type[insight_type].append(insight.get("content", {}))
        
        # Format each type
        type_formatters = {
            "trend": self._format_trend,
            "trending_topic": self._format_trend,
            "pain_point": self._format_pain_point,
            "content_gap": self._format_content_gap,
            "keyword": self._format_keyword,
            "engagement_pattern": self._format_engagement_pattern,
            "competitor_learning": self._format_competitor_learning,
            "emerging_trend": self._format_simple,
            "common_question": self._format_simple,
            "quick_win": self._format_simple,
        }
        
        for insight_type, contents in insights_by_type.items():
            formatter = type_formatters.get(insight_type, self._format_generic)
            section_header = insight_type.replace("_", " ").title()
            
            formatted_items = []
            for content in contents:
                formatted_items.append(formatter(content))
            
            formatted_sections.append(f"## {section_header}s\n" + "\n".join(formatted_items))
        
        return "\n\n".join(formatted_sections)
    
    def _format_trend(self, content: Any) -> str:
        """Format a trend insight."""
        if isinstance(content, dict):
            topic = content.get("topic", "Unknown topic")
            strength = content.get("trend_strength", "medium")
            evidence = content.get("evidence", "")
            angle = content.get("content_angle", "")
            return f"- **{topic}** (Strength: {strength})\n  Evidence: {evidence}\n  Suggested Angle: {angle}"
        return f"- {content}"
    
    def _format_pain_point(self, content: Any) -> str:
        """Format a pain point insight."""
        if isinstance(content, dict):
            pain = content.get("pain_point", "Unknown")
            severity = content.get("severity", "medium")
            evidence = content.get("evidence", "")
            opportunity = content.get("content_opportunity", "")
            return f"- **{pain}** (Severity: {severity})\n  Evidence: {evidence}\n  Content Opportunity: {opportunity}"
        return f"- {content}"
    
    def _format_content_gap(self, content: Any) -> str:
        """Format a content gap insight."""
        if isinstance(content, dict):
            gap = content.get("gap", "Unknown gap")
            size = content.get("opportunity_size", "medium")
            why = content.get("why_underserved", "")
            suggested = content.get("suggested_content", [])
            if isinstance(suggested, list):
                suggested = ", ".join(suggested[:3])
            return f"- **{gap}** (Opportunity: {size})\n  Why underserved: {why}\n  Suggested content: {suggested}"
        return f"- {content}"
    
    def _format_keyword(self, content: Any) -> str:
        """Format a keyword insight."""
        if isinstance(content, dict):
            keyword = content.get("keyword", "Unknown")
            intent = content.get("search_intent", "")
            competition = content.get("competition", "medium")
            recommendation = content.get("content_recommendation", "")
            return f"- **{keyword}** (Intent: {intent}, Competition: {competition})\n  Recommendation: {recommendation}"
        return f"- {content}"
    
    def _format_engagement_pattern(self, content: Any) -> str:
        """Format an engagement pattern insight."""
        if isinstance(content, dict):
            pattern = content.get("pattern", "Unknown")
            engagement_type = content.get("engagement_type", "")
            application = content.get("application", "")
            return f"- **{pattern}** (Type: {engagement_type})\n  How to apply: {application}"
        return f"- {content}"
    
    def _format_competitor_learning(self, content: Any) -> str:
        """Format a competitor learning insight."""
        if isinstance(content, dict):
            name = content.get("name", "Unknown")
            what_works = content.get("what_works", "")
            learnings = content.get("learnings", "")
            return f"- **{name}**\n  What works: {what_works}\n  Learning: {learnings}"
        return f"- {content}"
    
    def _format_simple(self, content: Any) -> str:
        """Format a simple string insight."""
        if isinstance(content, dict):
            return f"- {json.dumps(content)}"
        return f"- {content}"
    
    def _format_generic(self, content: Any) -> str:
        """Format any generic insight."""
        if isinstance(content, dict):
            return f"- {json.dumps(content, indent=2)}"
        return f"- {content}"
    
    def _build_generation_prompt(
        self,
        insights_context: str,
        niche: str,
        target_audience: str,
        tone: str,
        style_guide: Dict[str, Any],
        ideas_count: int
    ) -> str:
        """Build the content generation prompt."""
        
        hook_style = style_guide.get("hook_style", "Question or bold statement")
        content_style = style_guide.get("content_style", "Fast-paced, value-packed")
        cta_style = style_guide.get("cta_style", "Save and share focused")
        avoid_list = style_guide.get("avoid", [])
        avoid_str = ", ".join(avoid_list) if avoid_list else "None specified"
        
        prompt = f"""Based on the following research insights, generate {ideas_count} highly engaging Instagram Reel content ideas.

# CONTEXT
Niche: {niche}
Target Audience: {target_audience}
Tone: {tone}

# STYLE GUIDE
- Hook Style: {hook_style}
- Content Style: {content_style}
- CTA Style: {cta_style}
- Avoid: {avoid_str}

# SELECTED INSIGHTS TO USE
{insights_context}

# YOUR TASK
Create {ideas_count} unique, viral-worthy content ideas that directly address the insights above. Each idea should:
1. Be based on one or more of the provided insights
2. Have a scroll-stopping hook
3. Provide real value to the target audience
4. Be achievable as a 30-60 second Reel

# OUTPUT FORMAT
Return a JSON array with exactly {ideas_count} ideas. Each idea should have this structure:
```json
[
  {{
    "title": "Short, catchy title for the content",
    "hook": "The opening line/hook that grabs attention",
    "concept": "Brief description of what the content covers",
    "key_points": ["Point 1", "Point 2", "Point 3"],
    "content_structure": "How the content flows (e.g., hook → problem → solution → CTA)",
    "cta": "Call to action",
    "insight_source": "Which insight(s) this idea is based on",
    "engagement_prediction": "high/medium/low",
    "why_it_works": "Brief explanation of why this will resonate"
  }}
]
```

Return ONLY the JSON array, no other text."""

        return prompt
    
    def _parse_ideas_response(self, response: str) -> List[Dict[str, Any]]:
        """Parse the AI response into a list of ideas."""
        try:
            # Clean up response - remove markdown code blocks if present
            cleaned = response.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            elif cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()
            
            ideas = json.loads(cleaned)
            
            if not isinstance(ideas, list):
                logger.error("Response is not a list")
                return []
            
            # Validate and clean each idea
            valid_ideas = []
            for idea in ideas:
                if isinstance(idea, dict) and idea.get("title"):
                    # Ensure all expected fields exist
                    valid_idea = {
                        "title": idea.get("title", ""),
                        "hook": idea.get("hook", ""),
                        "concept": idea.get("concept", idea.get("description", "")),
                        "key_points": idea.get("key_points", []),
                        "content_structure": idea.get("content_structure", ""),
                        "cta": idea.get("cta", ""),
                        "insight_source": idea.get("insight_source", ""),
                        "engagement_prediction": idea.get("engagement_prediction", "medium"),
                        "why_it_works": idea.get("why_it_works", ""),
                        "status": "pending",
                        "source": "insights",
                        "created_at": datetime.now().isoformat()
                    }
                    valid_ideas.append(valid_idea)
            
            return valid_ideas
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse ideas response: {e}")
            logger.debug(f"Raw response: {response[:500]}...")
            return []
    
    def _generate_scripts_for_ideas(
        self,
        ideas: List[Dict[str, Any]],
        persona: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate full scripts for the generated ideas."""
        basic_info = persona.get("basic_info", {})
        style_guide = persona.get("style_guide", {})
        
        scripts = []
        
        for idx, idea in enumerate(ideas):
            logger.info(f"Generating script {idx + 1}/{len(ideas)}: {idea.get('title', 'Untitled')}")
            
            script_prompt = self._build_script_prompt(idea, basic_info, style_guide)
            
            try:
                script_response = self.ai_client.generate(
                    prompt=script_prompt,
                    system_prompt="You are an expert scriptwriter for short-form video content. Write engaging, fast-paced scripts that hook viewers and deliver value."
                )
                
                script = self._parse_script_response(script_response, idea)
                scripts.append(script)
                
            except Exception as e:
                logger.error(f"Error generating script for idea '{idea.get('title')}': {e}")
                # Add a placeholder script on error
                scripts.append({
                    "title": idea.get("title", "Untitled"),
                    "idea_title": idea.get("title", ""),
                    "error": str(e),
                    "source": "insights",
                    "status": "error"
                })
        
        return scripts
    
    def _build_script_prompt(
        self,
        idea: Dict[str, Any],
        basic_info: Dict[str, Any],
        style_guide: Dict[str, Any]
    ) -> str:
        """Build the script generation prompt."""
        
        tone = basic_info.get("tone", "engaging")
        avoid_list = style_guide.get("avoid", [])
        avoid_str = ", ".join(avoid_list) if avoid_list else "None"
        
        key_points = idea.get("key_points", [])
        key_points_str = "\n".join([f"  - {p}" for p in key_points]) if key_points else "  - Not specified"
        
        prompt = f"""Write a complete script for a 30-60 second Instagram Reel based on this content idea:

# CONTENT IDEA
Title: {idea.get('title', 'Untitled')}
Hook: {idea.get('hook', '')}
Concept: {idea.get('concept', '')}
Key Points:
{key_points_str}
Content Structure: {idea.get('content_structure', '')}
CTA: {idea.get('cta', '')}

# STYLE REQUIREMENTS
- Tone: {tone}
- Avoid: {avoid_str}
- Make it punchy and fast-paced
- Every line should be speakable in 3-5 seconds
- Total runtime: 30-60 seconds

# OUTPUT FORMAT
Return a JSON object with this structure:
```json
{{
  "title": "Script title",
  "hook": "Opening hook line (first 3 seconds)",
  "main_content": [
    "Line 1 of the main content",
    "Line 2 of the main content",
    "..."
  ],
  "cta": "Call to action line",
  "full_script": "Complete script as a single text block",
  "speaker_notes": "Notes for delivery (pace, emphasis, etc.)",
  "estimated_duration": "30-45 seconds"
}}
```

Return ONLY the JSON object, no other text."""

        return prompt
    
    def _parse_script_response(
        self,
        response: str,
        idea: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Parse the script response."""
        try:
            # Clean up response
            cleaned = response.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            elif cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()
            
            script = json.loads(cleaned)
            
            # Add metadata
            script["idea_title"] = idea.get("title", "")
            script["insight_source"] = idea.get("insight_source", "")
            script["source"] = "insights"
            script["status"] = "pending"
            script["created_at"] = datetime.now().isoformat()
            
            return script
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse script response: {e}")
            # Return a basic script structure with the raw response
            return {
                "title": idea.get("title", "Untitled"),
                "idea_title": idea.get("title", ""),
                "hook": idea.get("hook", ""),
                "main_content": [response[:500] if response else "Script generation failed"],
                "cta": idea.get("cta", ""),
                "full_script": response if response else "Script generation failed",
                "source": "insights",
                "status": "needs_review",
                "created_at": datetime.now().isoformat()
            }


def generate_content_from_insights(
    selected_insights: List[Dict[str, Any]],
    persona: Dict[str, Any],
    ideas_count: int = 5,
    generate_scripts: bool = True,
    ai_client: Optional[AIClient] = None
) -> Dict[str, Any]:
    """
    Convenience function to generate content from insights.
    
    Args:
        selected_insights: List of selected insight items
        persona: Persona dictionary
        ideas_count: Number of ideas to generate
        generate_scripts: Whether to also generate scripts
        ai_client: Optional AI client
        
    Returns:
        Dictionary with generated content
    """
    generator = InsightsContentGenerator(ai_client=ai_client)
    return generator.generate_content_from_insights(
        selected_insights=selected_insights,
        persona=persona,
        ideas_count=ideas_count,
        generate_scripts=generate_scripts
    )
