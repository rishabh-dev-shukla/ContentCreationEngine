"""
Persona Manager Module.
Manages user personas, style guides, and learns from past content.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from collections import Counter

from config.settings import settings

logger = logging.getLogger(__name__)


class PersonaManager:
    """Manages user personas and learns from past content."""
    
    def __init__(self, personas_dir: Optional[Path] = None):
        """
        Initialize the PersonaManager.
        
        Args:
            personas_dir: Directory containing persona JSON files.
        """
        self.personas_dir = personas_dir or settings.personas_dir
        self.personas_dir.mkdir(parents=True, exist_ok=True)
        self._personas_cache: Dict[str, Dict[str, Any]] = {}
    
    def list_personas(self) -> List[str]:
        """
        List all available persona IDs.
        
        Returns:
            List of persona IDs (filenames without .json extension)
        """
        personas = []
        for file_path in self.personas_dir.glob("*.json"):
            if not file_path.name.startswith("_"):  # Skip internal files
                personas.append(file_path.stem)
        return personas
    
    def load_persona(self, persona_id: str, use_cache: bool = True) -> Dict[str, Any]:
        """
        Load a persona by ID.
        
        Args:
            persona_id: The persona identifier (filename without .json)
            use_cache: Whether to use cached version if available
            
        Returns:
            Persona dictionary
        """
        # Check cache first
        if use_cache and persona_id in self._personas_cache:
            return self._personas_cache[persona_id]
        
        file_path = self.personas_dir / f"{persona_id}.json"
        
        if not file_path.exists():
            logger.error(f"Persona not found: {persona_id}")
            raise FileNotFoundError(f"Persona '{persona_id}' not found at {file_path}")
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                persona = json.load(f)
            
            # Cache the persona
            self._personas_cache[persona_id] = persona
            logger.info(f"Loaded persona: {persona_id}")
            return persona
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in persona file {persona_id}: {e}")
            raise
    
    def save_persona(self, persona: Dict[str, Any]) -> str:
        """
        Save a persona to file.
        
        Args:
            persona: Persona dictionary (must contain 'persona_id')
            
        Returns:
            The persona_id of the saved persona
        """
        persona_id = persona.get("persona_id")
        if not persona_id:
            raise ValueError("Persona must have a 'persona_id' field")
        
        file_path = self.personas_dir / f"{persona_id}.json"
        
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(persona, f, indent=2, ensure_ascii=False)
            
            # Update cache
            self._personas_cache[persona_id] = persona
            logger.info(f"Saved persona: {persona_id}")
            return persona_id
            
        except Exception as e:
            logger.error(f"Failed to save persona {persona_id}: {e}")
            raise
    
    def create_persona(
        self,
        persona_id: str,
        name: str,
        niche: str,
        target_audience: str,
        tone: str = "Friendly and engaging",
        **kwargs
    ) -> Dict[str, Any]:
        """
        Create a new persona with default structure.
        
        Args:
            persona_id: Unique identifier for the persona
            name: Display name
            niche: Content niche (e.g., "SAT Exam Preparation")
            target_audience: Target audience description
            tone: Content tone
            **kwargs: Additional basic_info fields
            
        Returns:
            The created persona dictionary
        """
        persona = {
            "persona_id": persona_id,
            "basic_info": {
                "name": name,
                "niche": niche,
                "target_audience": target_audience,
                "tone": tone,
                "unique_angle": kwargs.get("unique_angle", ""),
                "hashtags": kwargs.get("hashtags", []),
                "posting_frequency": kwargs.get("posting_frequency", "daily")
            },
            "style_guide": {
                "hook_style": kwargs.get("hook_style", "Question or bold statement"),
                "content_style": kwargs.get("content_style", "Fast-paced, value-packed"),
                "cta_style": kwargs.get("cta_style", "Save and share focused"),
                "avoid": kwargs.get("avoid", []),
                "visual_preferences": {
                    "colors": kwargs.get("colors", []),
                    "style": kwargs.get("visual_style", "Clean and modern"),
                    "text_style": kwargs.get("text_style", "Bold and readable")
                }
            },
            "existing_reels": [],
            "scripts": [],
            "learned_patterns": {
                "auto_generated": False,
                "last_updated": None,
                "best_performing_hooks": [],
                "avg_script_length": 0,
                "common_topics": [],
                "engagement_insights": {
                    "best_posting_time": None,
                    "avg_engagement_rate": None,
                    "top_performing_format": None
                }
            },
            "content_preferences": {
                "preferred_topics": [],
                "avoid_topics": []
            }
        }
        
        self.save_persona(persona)
        return persona
    
    def add_reel(
        self,
        persona_id: str,
        title: str,
        script: str,
        engagement: Optional[Dict[str, int]] = None,
        date: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Add a new reel to persona's history.
        
        Args:
            persona_id: The persona identifier
            title: Reel title
            script: Full script text
            engagement: Engagement metrics (views, likes, comments, etc.)
            date: Date of posting (ISO format)
            **kwargs: Additional reel metadata
            
        Returns:
            Updated persona dictionary
        """
        persona = self.load_persona(persona_id, use_cache=False)
        
        # Generate reel ID
        existing_reels = persona.get("existing_reels", [])
        reel_id = f"reel_{len(existing_reels) + 1:03d}"
        
        reel = {
            "id": reel_id,
            "title": title,
            "script": script,
            "engagement": engagement or {
                "views": 0,
                "likes": 0,
                "comments": 0,
                "shares": 0,
                "saves": 0
            },
            "date": date or datetime.now().strftime("%Y-%m-%d"),
            "performance_notes": kwargs.get("performance_notes", "")
        }
        
        # Add any extra metadata
        for key, value in kwargs.items():
            if key not in reel:
                reel[key] = value
        
        existing_reels.append(reel)
        persona["existing_reels"] = existing_reels
        
        # Trigger learning update
        self._update_learned_patterns(persona)
        
        self.save_persona(persona)
        logger.info(f"Added reel '{title}' to persona {persona_id}")
        return persona
    
    def update_engagement(
        self,
        persona_id: str,
        reel_id: str,
        engagement: Dict[str, int]
    ) -> Dict[str, Any]:
        """
        Update engagement metrics for a specific reel.
        
        Args:
            persona_id: The persona identifier
            reel_id: The reel identifier
            engagement: Updated engagement metrics
            
        Returns:
            Updated persona dictionary
        """
        persona = self.load_persona(persona_id, use_cache=False)
        
        for reel in persona.get("existing_reels", []):
            if reel.get("id") == reel_id:
                reel["engagement"] = engagement
                break
        
        # Trigger learning update
        self._update_learned_patterns(persona)
        
        self.save_persona(persona)
        logger.info(f"Updated engagement for reel {reel_id}")
        return persona
    
    def _update_learned_patterns(self, persona: Dict[str, Any]) -> None:
        """
        Automatically update learned patterns based on existing reels.
        
        Args:
            persona: Persona dictionary to update (modified in place)
        """
        existing_reels = persona.get("existing_reels", [])
        
        if not existing_reels:
            return
        
        learned = persona.get("learned_patterns", {})
        learned["auto_generated"] = True
        learned["last_updated"] = datetime.now().isoformat()
        
        # Calculate average script length
        script_lengths = [len(reel.get("script", "").split()) for reel in existing_reels]
        learned["avg_script_length"] = int(sum(script_lengths) / len(script_lengths)) if script_lengths else 0
        
        # Find best performing hooks
        reels_with_engagement = [
            reel for reel in existing_reels 
            if reel.get("engagement", {}).get("views", 0) > 0
        ]
        
        if reels_with_engagement:
            # Sort by engagement rate (saves + shares are weighted higher)
            def engagement_score(reel):
                eng = reel.get("engagement", {})
                views = eng.get("views", 1)
                return (
                    eng.get("likes", 0) + 
                    eng.get("comments", 0) * 2 + 
                    eng.get("shares", 0) * 3 + 
                    eng.get("saves", 0) * 3
                ) / views
            
            sorted_reels = sorted(reels_with_engagement, key=engagement_score, reverse=True)
            
            # Extract hooks from top performers (first sentence of script)
            best_hooks = []
            for reel in sorted_reels[:5]:
                script = reel.get("script", "")
                first_sentence = script.split(".")[0] + "." if "." in script else script[:100]
                best_hooks.append({
                    "hook": first_sentence,
                    "title": reel.get("title", ""),
                    "engagement_score": engagement_score(reel)
                })
            
            learned["best_performing_hooks"] = best_hooks
            
            # Calculate average engagement rate
            total_engagement_rate = sum(engagement_score(r) for r in reels_with_engagement)
            learned["engagement_insights"]["avg_engagement_rate"] = round(
                total_engagement_rate / len(reels_with_engagement), 4
            )
        
        # Extract common topics from titles
        all_words = []
        for reel in existing_reels:
            title = reel.get("title", "").lower()
            # Simple word extraction (could be improved with NLP)
            words = [w for w in title.split() if len(w) > 3]
            all_words.extend(words)
        
        word_counts = Counter(all_words)
        learned["common_topics"] = [word for word, count in word_counts.most_common(10)]
        
        persona["learned_patterns"] = learned
    
    def get_style_summary(self, persona_id: str) -> str:
        """
        Get a text summary of the persona's style for AI prompts.
        
        Args:
            persona_id: The persona identifier
            
        Returns:
            Formatted style summary string
        """
        persona = self.load_persona(persona_id)
        
        basic_info = persona.get("basic_info", {})
        style_guide = persona.get("style_guide", {})
        learned = persona.get("learned_patterns", {})
        
        summary = f"""
## Persona: {basic_info.get('name', 'Unknown')}

### Basic Info
- Niche: {basic_info.get('niche', 'Not specified')}
- Target Audience: {basic_info.get('target_audience', 'General')}
- Tone: {basic_info.get('tone', 'Friendly')}
- Unique Angle: {basic_info.get('unique_angle', 'Not specified')}

### Style Guide
- Hook Style: {style_guide.get('hook_style', 'Not specified')}
- Content Style: {style_guide.get('content_style', 'Not specified')}
- CTA Style: {style_guide.get('cta_style', 'Not specified')}
- Avoid: {', '.join(style_guide.get('avoid', []))}

### Learned Patterns
- Average Script Length: {learned.get('avg_script_length', 'Unknown')} words
- Common Topics: {', '.join(learned.get('common_topics', []))}
"""
        
        # Add best performing hooks if available
        best_hooks = learned.get("best_performing_hooks", [])
        if best_hooks:
            summary += "\n### Best Performing Hooks\n"
            for hook in best_hooks[:3]:
                summary += f"- {hook.get('hook', '')}\n"
        
        return summary.strip()
    
    def get_persona_for_generation(self, persona_id: str) -> Dict[str, Any]:
        """
        Get a persona optimized for content generation.
        Includes computed fields and learned patterns.
        
        Args:
            persona_id: The persona identifier
            
        Returns:
            Persona dictionary with additional computed fields
        """
        persona = self.load_persona(persona_id)
        
        # Ensure learned patterns are up to date
        self._update_learned_patterns(persona)
        
        # Add style summary for easy access
        persona["_style_summary"] = self.get_style_summary(persona_id)
        
        # Add sample scripts for reference
        existing_reels = persona.get("existing_reels", [])
        if existing_reels:
            # Get top 3 performing scripts
            sorted_reels = sorted(
                existing_reels,
                key=lambda r: sum(r.get("engagement", {}).values()),
                reverse=True
            )
            persona["_sample_scripts"] = [
                reel.get("script", "") for reel in sorted_reels[:3]
            ]
        
        return persona
    
    def clear_cache(self, persona_id: Optional[str] = None) -> None:
        """
        Clear the persona cache.
        
        Args:
            persona_id: Specific persona to clear, or None for all
        """
        if persona_id:
            self._personas_cache.pop(persona_id, None)
        else:
            self._personas_cache.clear()
        logger.info(f"Cleared cache for: {persona_id or 'all personas'}")
