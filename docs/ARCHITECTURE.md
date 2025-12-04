# Content Creation Engine - Architecture & Flow

## Overview

The Content Creation Engine is an automated system that generates Instagram Reel content ideas, scripts, and visual suggestions based on trending topics in a specific niche.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        CONTENT CREATION ENGINE                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐             │
│   │ RESEARCH │ => │  IDEAS   │ => │ SCRIPTS  │ => │ VISUALS  │ => OUTPUT   │
│   │ (Scrape) │    │(Generate)│    │ (Write)  │    │(Suggest) │    (JSON)   │
│   └──────────┘    └──────────┘    └──────────┘    └──────────┘             │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Directory Structure

```
ContentCreationEngine/
│
├── main.py                      # Entry point - starts the engine
├── config/
│   ├── settings.py              # Configuration & environment variables
│   └── prompts/                 # AI prompt templates
│       ├── idea_generation.txt
│       ├── script_writing.txt
│       └── visual_suggestions.txt
│
├── src/content_creation_engine/
│   ├── scrapers/                # Data collection modules
│   │   ├── reddit_scraper.py
│   │   ├── news_scraper.py
│   │   └── instagram_scraper.py
│   │
│   ├── generators/              # AI content generation
│   │   ├── idea_generator.py
│   │   ├── script_writer.py
│   │   └── visual_suggester.py
│   │
│   ├── persona/                 # User persona management
│   │   └── persona_manager.py
│   │
│   ├── scheduler/               # Workflow orchestration
│   │   └── daily_workflow.py
│   │
│   └── utils/                   # Utilities
│       └── ai_client.py         # Multi-provider AI client
│
├── data/
│   ├── personas/                # User persona JSON files
│   ├── output/                  # Generated content (JSON)
│   └── research_cache/          # Cached research data
│
└── tests/                       # Test suite
```

---

## Complete Flow Diagram

```
                                    ┌─────────────────┐
                                    │    main.py      │
                                    │   Entry Point   │
                                    └────────┬────────┘
                                             │
                                             ▼
                                    ┌─────────────────┐
                                    │ ContentPipeline │
                                    │  (Orchestrator) │
                                    └────────┬────────┘
                                             │
                         ┌───────────────────┼───────────────────┐
                         │                   │                   │
                         ▼                   ▼                   ▼
              ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
              │  PersonaManager  │ │    AIClient      │ │    Scrapers      │
              │  Load user style │ │ (DeepSeek/GPT)   │ │ Reddit/News/IG   │
              └────────┬─────────┘ └────────┬─────────┘ └────────┬─────────┘
                       │                    │                    │
                       └───────────────────┬┴────────────────────┘
                                           │
                                           ▼
                              ┌────────────────────────┐
                              │   STEP 1: RESEARCH     │
                              │   Scrape trending      │
                              │   topics from sources  │
                              └───────────┬────────────┘
                                          │
                                          ▼
                              ┌────────────────────────┐
                              │   STEP 2: IDEATION     │
                              │   AI generates 5       │
                              │   content ideas        │
                              └───────────┬────────────┘
                                          │
                                          ▼
                              ┌────────────────────────┐
                              │   STEP 3: SCRIPTING    │
                              │   AI writes script     │
                              │   for each idea        │
                              └───────────┬────────────┘
                                          │
                                          ▼
                              ┌────────────────────────┐
                              │   STEP 4: VISUALS      │
                              │   AI suggests visuals  │
                              │   for each script      │
                              └───────────┬────────────┘
                                          │
                                          ▼
                              ┌────────────────────────┐
                              │   STEP 5: OUTPUT       │
                              │   Save to JSON file    │
                              │   data/output/         │
                              └────────────────────────┘
```

---

## Detailed Component Breakdown

### 1. Entry Point (`main.py`)

```python
# What happens when you run: python main.py --persona sat_prep_guru --ideas 5

1. Parse command line arguments
2. Load configuration from .env
3. Initialize ContentPipeline
4. Run pipeline with specified persona
5. Save output to JSON
```

**Command Options:**
- `--persona <name>` - Which persona to use
- `--ideas <count>` - How many ideas to generate (default: 5)
- `--no-schedule` - Run once without scheduling
- `--schedule` - Run daily at configured time (8 AM)

---

### 2. Configuration (`config/settings.py`)

Loads all settings from environment variables:

```
┌─────────────────────────────────────────────────────────┐
│                    SETTINGS                              │
├─────────────────────────────────────────────────────────┤
│ AI Settings:                                            │
│   - OpenAI API Key                                      │
│   - DeepSeek API Key                                    │
│   - Default Provider (deepseek)                         │
│                                                         │
│ Scraper Settings:                                       │
│   - Reddit credentials                                  │
│   - NewsAPI key                                         │
│   - Instagram token                                     │
│                                                         │
│ Content Settings:                                       │
│   - Ideas per day: 5                                    │
│   - Script length: 150-200 words                        │
│   - Default niche: "SAT Exam Preparation"               │
│                                                         │
│ Paths:                                                  │
│   - Personas: data/personas/                            │
│   - Output: data/output/                                │
│   - Cache: data/research_cache/                         │
└─────────────────────────────────────────────────────────┘
```

---

### 3. Persona Manager (`persona/persona_manager.py`)

Manages user personas - the "voice" and style for content.

```
┌─────────────────────────────────────────────────────────┐
│                 PERSONA (JSON File)                      │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  basic_info:                                            │
│    - name: "SAT Prep Guru"                              │
│    - niche: "SAT Exam Preparation"                      │
│    - target_audience: "High school students (16-18)"    │
│    - tone: "Friendly, encouraging, humorous"            │
│                                                         │
│  style_guide:                                           │
│    - hook_style: "Question or shocking statistic"       │
│    - content_style: "Numbered tips, fast-paced"         │
│    - cta_style: "Save and share focused"                │
│    - avoid: ["Complex jargon", "Negative messaging"]    │
│                                                         │
│  existing_reels:                                        │
│    - Past scripts with engagement metrics               │
│    - Used for AI to learn your style                    │
│                                                         │
│  learned_patterns:                                      │
│    - Auto-analyzed from your past content               │
│    - Best performing hooks                              │
│    - Common topics                                      │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**Key Functions:**
- `load_persona(id)` - Load persona from JSON file
- `get_style_summary(id)` - Get formatted style for AI prompts
- `add_reel(id, title, script, engagement)` - Add new content to history
- Auto-learning: Analyzes engagement to find patterns

---

### 4. Scrapers (`scrapers/`)

Collect trending topics from multiple sources.

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ Reddit Scraper  │    │  News Scraper   │    │Instagram Scraper│
├─────────────────┤    ├─────────────────┤    ├─────────────────┤
│                 │    │                 │    │                 │
│ Uses: PRAW      │    │ Uses: NewsAPI   │    │ Uses: Graph API │
│                 │    │                 │    │                 │
│ Scrapes:        │    │ Scrapes:        │    │ Scrapes:        │
│ - r/SAT         │    │ - Education     │    │ - #SATprep      │
│ - r/SATprep     │    │   news articles │    │ - #StudyTips    │
│ - r/ACT         │    │ - Test prep     │    │ - Trending      │
│                 │    │   blogs         │    │   hashtags      │
│                 │    │                 │    │                 │
│ Returns:        │    │ Returns:        │    │ Returns:        │
│ - Post titles   │    │ - Headlines     │    │ - Top posts     │
│ - Discussions   │    │ - Descriptions  │    │ - Engagement    │
│ - Engagement    │    │ - Sources       │    │ - Trends        │
│                 │    │                 │    │                 │
└────────┬────────┘    └────────┬────────┘    └────────┬────────┘
         │                      │                      │
         └──────────────────────┴──────────────────────┘
                                │
                                ▼
                    ┌───────────────────────┐
                    │   Combined Research   │
                    │   Data Dictionary     │
                    └───────────────────────┘
```

**Output Format:**
```python
{
    "reddit": [
        {"title": "...", "score": 450, "subreddit": "SAT", ...},
        ...
    ],
    "news": [
        {"headline": "...", "source": "Education Week", ...},
        ...
    ],
    "instagram": [
        {"hashtag": "#SATprep", "top_posts": [...], ...},
        ...
    ]
}
```

---

### 5. AI Client (`utils/ai_client.py`)

Unified interface for multiple AI providers.

```
┌─────────────────────────────────────────────────────────┐
│                     AI CLIENT                            │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Supported Providers:                                   │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐                 │
│  │ OpenAI  │  │DeepSeek │  │  Grok   │                 │
│  │ GPT-4   │  │  Chat   │  │  Beta   │                 │
│  └─────────┘  └─────────┘  └─────────┘                 │
│                                                         │
│  Methods:                                               │
│  - generate(prompt, system_message, temperature)        │
│  - Automatic provider selection based on .env           │
│  - Error handling and retries                           │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

### 6. Generators (`generators/`)

AI-powered content generation modules.

#### A. Idea Generator (`idea_generator.py`)

```
┌─────────────────────────────────────────────────────────┐
│                  IDEA GENERATOR                          │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  INPUT:                                                 │
│  - Research data (Reddit, News, Instagram)              │
│  - Persona (niche, audience, style)                     │
│  - Number of ideas to generate                          │
│                                                         │
│  PROCESS:                                               │
│  1. Format research data into prompt                    │
│  2. Load idea_generation.txt template                   │
│  3. Send to AI with persona context                     │
│  4. Parse JSON response                                 │
│                                                         │
│  OUTPUT (5 ideas):                                      │
│  [                                                      │
│    {                                                    │
│      "id": 1,                                           │
│      "title": "3 SAT Math Shortcuts...",                │
│      "concept": "Cover little-known...",                │
│      "why_it_works": "Students anxious...",             │
│      "trending_angle": "Digital SAT...",                │
│      "engagement_potential": "High"                     │
│    },                                                   │
│    ...                                                  │
│  ]                                                      │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

#### B. Script Writer (`script_writer.py`)

```
┌─────────────────────────────────────────────────────────┐
│                   SCRIPT WRITER                          │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  INPUT:                                                 │
│  - Content idea (title, concept)                        │
│  - Persona style guide                                  │
│  - Past successful scripts (for learning)               │
│                                                         │
│  PROCESS:                                               │
│  1. Load script_writing.txt template                    │
│  2. Include persona's best hooks & CTAs                 │
│  3. Send to AI with style instructions                  │
│  4. Parse JSON response                                 │
│                                                         │
│  OUTPUT (per idea):                                     │
│  {                                                      │
│    "hook": "Did you know 90% of students...",           │
│    "main_content": "Here are 3 shortcuts...",           │
│    "cta": "Save this for test day!",                    │
│    "full_script": "Complete script...",                 │
│    "word_count": 175,                                   │
│    "estimated_duration_seconds": 45,                    │
│    "speaker_notes": "Emphasize..."                      │
│  }                                                      │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

#### C. Visual Suggester (`visual_suggester.py`)

```
┌─────────────────────────────────────────────────────────┐
│                  VISUAL SUGGESTER                        │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  INPUT:                                                 │
│  - Script (hook, main_content, cta)                     │
│  - Original idea                                        │
│  - Persona visual preferences                           │
│                                                         │
│  OUTPUT:                                                │
│  {                                                      │
│    "b_roll": [                                          │
│      {"timestamp": "0-3s", "description": "..."}        │
│    ],                                                   │
│    "text_overlays": [                                   │
│      {"timestamp": "0-3s", "text": "STOP!",             │
│       "style": "Bold white", "animation": "Pop-in"}     │
│    ],                                                   │
│    "animations": [...],                                 │
│    "color_scheme": {                                    │
│      "primary": "#1E40AF",                              │
│      "secondary": "#FFFFFF",                            │
│      "mood": "Energetic"                                │
│    },                                                   │
│    "music_suggestions": {                               │
│      "genre": "Upbeat lo-fi",                           │
│      "tempo": "Medium-fast"                             │
│    },                                                   │
│    "shot_list": [...]                                   │
│  }                                                      │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

### 7. Daily Workflow (`scheduler/daily_workflow.py`)

Orchestrates the entire pipeline.

```
┌─────────────────────────────────────────────────────────┐
│                  CONTENT PIPELINE                        │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  run(persona_id, ideas_count=5):                        │
│                                                         │
│  ┌─────────────────────────────────────────────┐        │
│  │ STEP 1: Load Persona                        │        │
│  │ persona_manager.get_persona_for_generation()│        │
│  └─────────────────────────────────────────────┘        │
│                     │                                   │
│                     ▼                                   │
│  ┌─────────────────────────────────────────────┐        │
│  │ STEP 2: Research (Scraping)                 │        │
│  │ - reddit_scraper.scrape(niche)              │        │
│  │ - news_scraper.scrape(niche)                │        │
│  │ - instagram_scraper.scrape(niche)           │        │
│  └─────────────────────────────────────────────┘        │
│                     │                                   │
│                     ▼                                   │
│  ┌─────────────────────────────────────────────┐        │
│  │ STEP 3: Generate Ideas                      │        │
│  │ idea_generator.generate_ideas(research,     │        │
│  │                               persona, 5)   │        │
│  └─────────────────────────────────────────────┘        │
│                     │                                   │
│                     ▼                                   │
│  ┌─────────────────────────────────────────────┐        │
│  │ STEP 4: Write Scripts                       │        │
│  │ script_writer.write_scripts_batch(ideas,    │        │
│  │                                   persona)  │        │
│  └─────────────────────────────────────────────┘        │
│                     │                                   │
│                     ▼                                   │
│  ┌─────────────────────────────────────────────┐        │
│  │ STEP 5: Generate Visuals                    │        │
│  │ visual_suggester.suggest_visuals_batch(     │        │
│  │                    scripts, ideas, persona) │        │
│  └─────────────────────────────────────────────┘        │
│                     │                                   │
│                     ▼                                   │
│  ┌─────────────────────────────────────────────┐        │
│  │ STEP 6: Save Output                         │        │
│  │ ContentOutput.save() => JSON file           │        │
│  └─────────────────────────────────────────────┘        │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

### 8. Output Format

Final output saved to `data/output/YYYY-MM-DD_persona_content.json`:

```json
{
  "date": "2025-12-02",
  "persona_id": "sat_prep_guru",
  "niche": "SAT Exam Preparation",
  
  "research_data": {
    "reddit": [...],
    "news": [...],
    "instagram": [...]
  },
  
  "content_ideas": [
    {
      "id": 1,
      "title": "3 Digital SAT Hacks Nobody Talks About",
      "concept": "Cover hidden features of the digital SAT...",
      "why_it_works": "Students anxious about new format",
      "trending_angle": "Digital SAT rollout",
      "engagement_potential": "High"
    }
  ],
  
  "scripts": [
    {
      "idea_id": 1,
      "hook": "The digital SAT has secret features...",
      "main_content": "Feature 1: The built-in Desmos...",
      "cta": "Save this before your test day!",
      "full_script": "Complete script here...",
      "word_count": 175,
      "estimated_duration_seconds": 45
    }
  ],
  
  "visuals": [
    {
      "idea_id": 1,
      "b_roll": [...],
      "text_overlays": [...],
      "color_scheme": {...},
      "music_suggestions": {...},
      "shot_list": [...]
    }
  ],
  
  "metadata": {
    "start_time": "2025-12-02T08:00:00",
    "end_time": "2025-12-02T08:02:30",
    "duration_seconds": 150,
    "ideas_generated": 5
  }
}
```

---

## Data Flow Summary

```
┌──────────────────────────────────────────────────────────────────────────┐
│                                                                          │
│  .env (API Keys)                                                         │
│       │                                                                  │
│       ▼                                                                  │
│  ┌─────────┐     ┌─────────┐     ┌─────────┐     ┌─────────┐            │
│  │ Reddit  │     │  News   │     │Instagram│     │ Persona │            │
│  │   API   │     │   API   │     │   API   │     │  JSON   │            │
│  └────┬────┘     └────┬────┘     └────┬────┘     └────┬────┘            │
│       │               │               │               │                  │
│       └───────────────┴───────┬───────┴───────────────┘                  │
│                               │                                          │
│                               ▼                                          │
│                    ┌─────────────────────┐                               │
│                    │   Content Pipeline  │                               │
│                    └──────────┬──────────┘                               │
│                               │                                          │
│                               ▼                                          │
│                    ┌─────────────────────┐                               │
│                    │   AI (DeepSeek)     │                               │
│                    │   Generate Content  │                               │
│                    └──────────┬──────────┘                               │
│                               │                                          │
│                               ▼                                          │
│                    ┌─────────────────────┐                               │
│                    │   Output JSON       │                               │
│                    │   5 Ideas + Scripts │                               │
│                    │   + Visual Guides   │                               │
│                    └─────────────────────┘                               │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## Quick Reference: Key Files

| File | Purpose |
|------|---------|
| `main.py` | Entry point - run this to start |
| `config/settings.py` | All configuration |
| `config/prompts/*.txt` | AI prompt templates |
| `data/personas/*.json` | Your persona definitions |
| `data/output/*.json` | Generated content |
| `src/.../daily_workflow.py` | Main pipeline logic |
| `src/.../ai_client.py` | AI provider interface |

---

## Running the Engine

```bash
# Basic run
python main.py --persona example_persona --ideas 5

# With scheduling (runs daily at 8 AM)
python main.py --persona example_persona --schedule

# Skip research (testing)
python main.py --persona example_persona --ideas 3 --skip-scraping
```
