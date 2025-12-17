"""
Insights Analyzer Module.
Extracts key insights, trends, and strategic data points from research data.
"""

import json
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path
from datetime import datetime

from config.settings import settings
from ..utils.ai_client import AIClient

logger = logging.getLogger(__name__)


class InsightsAnalyzer:
    """Analyzes research data to extract insights, trends, and strategic recommendations."""
    
    def __init__(self, ai_client: Optional[AIClient] = None):
        """
        Initialize the InsightsAnalyzer.
        
        Args:
            ai_client: Optional AI client instance. Creates one if not provided.
        """
        if ai_client:
            self.ai_client = ai_client
        else:
            # Use settings to determine provider and API key
            provider = settings.ai.default_provider
            api_key = self._get_api_key_for_provider(provider)
            self.ai_client = AIClient(provider=provider, api_key=api_key)
        
        self.insights_dir = settings.output_dir / "insights"
        self.insights_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_api_key_for_provider(self, provider: str) -> Optional[str]:
        """Get the appropriate API key for the given provider."""
        provider_keys = {
            "openai": settings.ai.openai_api_key,
            "deepseek": settings.ai.deepseek_api_key,
            "grok": settings.ai.grok_api_key
        }
        return provider_keys.get(provider.lower())
    
    def analyze_research_data(
        self,
        research_data: Dict[str, Any],
        persona: Dict[str, Any],
        analysis_types: List[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze research data and extract insights.
        
        Args:
            research_data: Dictionary containing scraped data from various sources
            persona: Persona dictionary with niche and audience info
            analysis_types: List of analysis types to perform. Default: all types
            
        Returns:
            Dictionary containing all extracted insights
        """
        if analysis_types is None:
            analysis_types = [
                "trending_topics",
                "audience_pain_points", 
                "content_gaps",
                "competitor_analysis",
                "engagement_patterns",
                "keyword_opportunities",
                "strategic_recommendations"
            ]
        
        basic_info = persona.get("basic_info", {})
        niche = basic_info.get("niche", "general")
        target_audience = basic_info.get("target_audience", "general audience")
        
        insights = {
            "generated_at": datetime.now().isoformat(),
            "persona_id": persona.get("persona_id", "unknown"),
            "niche": niche,
            "target_audience": target_audience,
            "data_sources_analyzed": self._get_data_source_stats(research_data),
            "analyses": {}
        }
        
        # Run each analysis type
        for analysis_type in analysis_types:
            try:
                logger.info(f"Running {analysis_type} analysis...")
                result = self._run_analysis(analysis_type, research_data, niche, target_audience)
                insights["analyses"][analysis_type] = result
            except Exception as e:
                logger.error(f"Error in {analysis_type} analysis: {e}")
                insights["analyses"][analysis_type] = {"error": str(e)}
        
        # Generate executive summary
        insights["executive_summary"] = self._generate_executive_summary(insights)
        
        return insights
    
    def _get_data_source_stats(self, research_data: Dict[str, Any]) -> Dict[str, int]:
        """Get statistics about data sources."""
        stats = {}
        for source, items in research_data.items():
            if isinstance(items, list):
                stats[source] = len(items)
        return stats
    
    def _run_analysis(
        self,
        analysis_type: str,
        research_data: Dict[str, Any],
        niche: str,
        target_audience: str
    ) -> Dict[str, Any]:
        """Run a specific type of analysis."""
        
        # Prepare condensed research data for the prompt
        condensed_data = self._condense_research_data(research_data)
        
        prompts = {
            "trending_topics": self._get_trending_topics_prompt(condensed_data, niche),
            "audience_pain_points": self._get_pain_points_prompt(condensed_data, niche, target_audience),
            "content_gaps": self._get_content_gaps_prompt(condensed_data, niche),
            "competitor_analysis": self._get_competitor_prompt(condensed_data, niche),
            "engagement_patterns": self._get_engagement_prompt(condensed_data, niche),
            "keyword_opportunities": self._get_keyword_prompt(condensed_data, niche),
            "strategic_recommendations": self._get_strategic_prompt(condensed_data, niche, target_audience)
        }
        
        prompt = prompts.get(analysis_type)
        if not prompt:
            return {"error": f"Unknown analysis type: {analysis_type}"}
        
        response = self.ai_client.generate(
            prompt=prompt,
            system_prompt="You are an expert market researcher and content strategist. Analyze the data thoroughly and provide actionable insights. Always respond with valid JSON.",
            temperature=0.7,
            max_tokens=2000
        )
        
        return self._parse_json_response(response)
    
    def _condense_research_data(self, research_data: Dict[str, Any]) -> str:
        """Condense research data into a readable format for AI analysis."""
        sections = []
        
        # YouTube data
        youtube = research_data.get("youtube", [])
        if youtube:
            yt_items = []
            for item in youtube[:15]:
                views = item.get("views", 0)
                likes = item.get("likes", 0)
                title = item.get("title", "")
                channel = item.get("channel", "")
                yt_items.append(f"- \"{title}\" by {channel} ({views:,} views, {likes:,} likes)")
            sections.append(f"### YouTube Videos ({len(youtube)} total):\n" + "\n".join(yt_items))
        
        # Instagram data
        instagram = research_data.get("instagram", [])
        if instagram:
            ig_items = []
            for item in instagram[:10]:
                views = item.get("views", 0)
                likes = item.get("likes", 0)
                title = item.get("title", item.get("caption", ""))[:100]
                ig_items.append(f"- \"{title}\" ({views:,} views, {likes:,} likes)")
            sections.append(f"### Instagram Posts ({len(instagram)} total):\n" + "\n".join(ig_items))
        
        # News data
        news = research_data.get("news", [])
        if news:
            news_items = []
            for item in news[:10]:
                title = item.get("title", "")
                source = item.get("source", "")
                summary = item.get("summary", "")[:150]
                news_items.append(f"- \"{title}\" ({source}): {summary}")
            sections.append(f"### News Articles ({len(news)} total):\n" + "\n".join(news_items))
        
        # Reddit data
        reddit = research_data.get("reddit", [])
        if reddit:
            reddit_items = []
            for item in reddit[:10]:
                title = item.get("title", "")
                subreddit = item.get("subreddit", "")
                score = item.get("score", 0)
                reddit_items.append(f"- r/{subreddit}: \"{title}\" ({score} upvotes)")
            sections.append(f"### Reddit Posts ({len(reddit)} total):\n" + "\n".join(reddit_items))
        
        # Serper/Google data
        serper = research_data.get("serper", [])
        if serper:
            serper_items = []
            for item in serper[:10]:
                title = item.get("title", "")
                snippet = item.get("snippet", item.get("description", ""))[:100]
                serper_items.append(f"- \"{title}\": {snippet}")
            sections.append(f"### Google Search Results ({len(serper)} total):\n" + "\n".join(serper_items))
        
        return "\n\n".join(sections)
    
    def _get_trending_topics_prompt(self, data: str, niche: str) -> str:
        return f"""Analyze this research data for the "{niche}" niche and identify trending topics.

{data}

Return a JSON object with:
{{
    "top_trends": [
        {{
            "topic": "topic name",
            "trend_strength": "high/medium/low",
            "evidence": "why this is trending",
            "content_angle": "how to create content around this"
        }}
    ],
    "emerging_trends": ["list of topics just starting to gain traction"],
    "declining_trends": ["topics losing interest"],
    "seasonal_relevance": "any time-sensitive opportunities"
}}"""

    def _get_pain_points_prompt(self, data: str, niche: str, audience: str) -> str:
        return f"""Analyze this research data for the "{niche}" niche targeting "{audience}".
Identify audience pain points, frustrations, and unmet needs.

{data}

Return a JSON object with:
{{
    "major_pain_points": [
        {{
            "pain_point": "description",
            "severity": "high/medium/low",
            "evidence": "where this was observed",
            "content_opportunity": "how to address this in content"
        }}
    ],
    "common_questions": ["frequently asked questions by the audience"],
    "misconceptions": ["common myths or misunderstandings"],
    "emotional_triggers": ["what emotionally resonates with this audience"]
}}"""

    def _get_content_gaps_prompt(self, data: str, niche: str) -> str:
        return f"""Analyze this research data for the "{niche}" niche.
Identify content gaps - topics that are underserved or not well-covered.

{data}

Return a JSON object with:
{{
    "content_gaps": [
        {{
            "gap": "description of missing content",
            "opportunity_size": "high/medium/low",
            "why_underserved": "reason this gap exists",
            "suggested_content": "specific content ideas to fill this gap"
        }}
    ],
    "oversaturated_topics": ["topics with too much competition"],
    "unique_angles": ["fresh perspectives not being explored"]
}}"""

    def _get_competitor_prompt(self, data: str, niche: str) -> str:
        return f"""Analyze this research data for the "{niche}" niche.
Identify competitor strategies and what's working for top performers.

{data}

Return a JSON object with:
{{
    "top_performers": [
        {{
            "name": "channel/account name",
            "what_works": "their successful strategies",
            "content_style": "their approach",
            "learnings": "what we can learn from them"
        }}
    ],
    "common_formats": ["popular content formats in this niche"],
    "differentiation_opportunities": ["ways to stand out from competitors"],
    "best_practices": ["proven tactics that work"]
}}"""

    def _get_engagement_prompt(self, data: str, niche: str) -> str:
        return f"""Analyze this research data for the "{niche}" niche.
Identify patterns in what drives engagement (views, likes, comments).

{data}

Return a JSON object with:
{{
    "high_engagement_patterns": [
        {{
            "pattern": "description",
            "engagement_type": "views/likes/comments/shares",
            "examples": "specific examples from data",
            "application": "how to apply this"
        }}
    ],
    "optimal_content_length": "recommended duration/length",
    "hook_styles": ["effective hook approaches"],
    "cta_patterns": ["effective call-to-action styles"],
    "posting_insights": "any timing or frequency observations"
}}"""

    def _get_keyword_prompt(self, data: str, niche: str) -> str:
        return f"""Analyze this research data for the "{niche}" niche.
Identify keyword and SEO/GEO (Generative Engine Optimization) opportunities.

{data}

Return a JSON object with:
{{
    "high_value_keywords": [
        {{
            "keyword": "keyword or phrase",
            "search_intent": "informational/transactional/navigational",
            "competition": "high/medium/low",
            "content_recommendation": "how to target this keyword"
        }}
    ],
    "long_tail_opportunities": ["specific long-tail keyword phrases"],
    "question_keywords": ["question-based search terms"],
    "geo_optimization": {{
        "ai_friendly_topics": "topics AI assistants frequently answer",
        "citation_opportunities": "content that could be cited by AI",
        "structured_data_suggestions": "ways to make content AI-readable"
    }}
}}"""

    def _get_strategic_prompt(self, data: str, niche: str, audience: str) -> str:
        return f"""Based on all this research data for the "{niche}" niche targeting "{audience}",
provide strategic recommendations for content creation and business growth.

{data}

Return a JSON object with:
{{
    "content_strategy": {{
        "primary_focus": "main content direction",
        "content_pillars": ["3-5 key content themes"],
        "content_mix": "recommended ratio of content types",
        "differentiation": "unique value proposition"
    }},
    "growth_opportunities": [
        {{
            "opportunity": "description",
            "potential_impact": "high/medium/low",
            "effort_required": "high/medium/low",
            "timeline": "short/medium/long term",
            "action_steps": ["specific steps to pursue this"]
        }}
    ],
    "risks_to_avoid": ["potential pitfalls or mistakes"],
    "quick_wins": ["immediate actions with fast results"],
    "long_term_plays": ["strategic investments for future growth"]
}}"""

    def _generate_executive_summary(self, insights: Dict[str, Any]) -> str:
        """Generate an executive summary of all insights."""
        analyses = insights.get("analyses", {})
        
        summary_prompt = f"""Based on these analysis results, write a concise executive summary (3-4 paragraphs).

Analyses performed:
{json.dumps(analyses, indent=2)[:4000]}

Write a clear, actionable executive summary highlighting:
1. Key findings and opportunities
2. Most important trends
3. Recommended immediate actions
4. Strategic direction

Return as plain text (not JSON)."""

        try:
            response = self.ai_client.generate(
                prompt=summary_prompt,
                system_prompt="You are a business strategist writing an executive brief. Be concise and actionable.",
                temperature=0.7,
                max_tokens=1000
            )
            if response is None:
                return "Executive summary generation failed - AI client not available. Please configure your API key."
            return response.strip()
        except Exception as e:
            logger.error(f"Error generating executive summary: {e}")
            return "Executive summary generation failed."
    
    def _parse_json_response(self, response: Optional[str]) -> Dict[str, Any]:
        """Parse JSON from AI response."""
        # Handle None response (AI client not initialized or API error)
        if response is None:
            logger.error("AI client returned None - check API key configuration")
            return {"error": "AI client not available. Please configure your API key in settings."}
        
        try:
            response = response.strip()
            
            # Handle markdown code blocks
            if "```json" in response:
                start = response.find("```json") + 7
                end = response.find("```", start)
                response = response[start:end].strip() if end != -1 else response[start:].strip()
            elif "```" in response:
                start = response.find("```") + 3
                end = response.find("```", start)
                response = response[start:end].strip() if end != -1 else response[start:].strip()
            
            return json.loads(response)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            return {"raw_response": response, "parse_error": str(e)}
    
    def save_insights(self, insights: Dict[str, Any], persona_id: str) -> Path:
        """Save insights to a JSON file."""
        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        filename = f"{timestamp}_{persona_id}_insights.json"
        
        persona_insights_dir = self.insights_dir / persona_id
        persona_insights_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = persona_insights_dir / filename
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(insights, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved insights to {file_path}")
        return file_path
    
    def get_latest_insights(self, persona_id: str) -> Optional[Dict[str, Any]]:
        """Get the most recent insights for a persona."""
        persona_insights_dir = self.insights_dir / persona_id
        
        if not persona_insights_dir.exists():
            return None
        
        files = sorted(persona_insights_dir.glob("*_insights.json"), reverse=True)
        if not files:
            return None
        
        with open(files[0], 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def list_insights(self, persona_id: str = None) -> List[Dict[str, Any]]:
        """List all available insights, optionally filtered by persona."""
        insights_list = []
        
        if persona_id:
            search_dirs = [self.insights_dir / persona_id]
        else:
            search_dirs = [d for d in self.insights_dir.iterdir() if d.is_dir()]
        
        for search_dir in search_dirs:
            if not search_dir.exists():
                continue
            
            for file_path in sorted(search_dir.glob("*_insights.json"), reverse=True):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        data['_file_path'] = str(file_path)
                        data['_filename'] = file_path.name
                        insights_list.append(data)
                except Exception as e:
                    logger.error(f"Error loading {file_path}: {e}")
        
        return insights_list
