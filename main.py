"""
ContentCreationEngine - Main Entry Point
Automated Content Creation Engine for Instagram Reels.
"""

import sys
import argparse
import logging
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from config.settings import settings
from src.content_creation_engine.scheduler import DailyWorkflow, ContentPipeline
from src.content_creation_engine.persona import PersonaManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("content_engine.log")
    ]
)
logger = logging.getLogger(__name__)


def run_pipeline(persona_id: str, ideas_count: int = 5, skip_scraping: bool = False):
    """Run the content generation pipeline once."""
    logger.info(f"Running content pipeline for persona: {persona_id}")
    
    pipeline = ContentPipeline()
    output = pipeline.run(
        persona_id=persona_id,
        ideas_count=ideas_count,
        skip_scraping=skip_scraping
    )
    
    print(f"\n{'='*60}")
    print(f"✅ Content Generation Complete!")
    print(f"{'='*60}")
    print(f"📅 Date: {output.date}")
    print(f"👤 Persona: {output.persona_id}")
    print(f"🎯 Niche: {output.niche}")
    print(f"💡 Ideas Generated: {len(output.ideas)}")
    print(f"📝 Scripts Written: {len(output.scripts)}")
    print(f"🎨 Visual Suggestions: {len(output.visuals)}")
    print(f"⏱️  Duration: {output.metadata.get('duration_seconds', 0):.2f} seconds")
    print(f"📁 Output: {output.metadata.get('output_file', 'N/A')}")
    print(f"{'='*60}\n")
    
    # Print summaries of generated ideas
    print("📌 Generated Content Ideas:")
    for i, idea in enumerate(output.ideas, 1):
        title = idea.get("title", "Untitled")
        print(f"   {i}. {title}")
    
    return output


def start_scheduler(persona_id: str, hour: int = 8, minute: int = 0):
    """Start the daily scheduler."""
    logger.info(f"Starting scheduler for persona: {persona_id} at {hour:02d}:{minute:02d}")
    
    workflow = DailyWorkflow()
    workflow.setup_scheduler(
        persona_id=persona_id,
        hour=hour,
        minute=minute,
        timezone=settings.scheduler.timezone
    )
    
    print(f"\n{'='*60}")
    print(f"🕐 Daily Scheduler Started")
    print(f"{'='*60}")
    print(f"👤 Persona: {persona_id}")
    print(f"⏰ Schedule: Daily at {hour:02d}:{minute:02d} {settings.scheduler.timezone}")
    print(f"💡 Ideas per day: {settings.content.ideas_per_day}")
    print(f"\nPress Ctrl+C to stop the scheduler...")
    print(f"{'='*60}\n")
    
    workflow.start()
    
    try:
        # Keep the main thread alive
        import time
        while True:
            time.sleep(60)
            next_run = workflow.get_next_run_time()
            if next_run:
                logger.debug(f"Next run scheduled for: {next_run}")
    except KeyboardInterrupt:
        print("\n\n⏹️  Stopping scheduler...")
        workflow.stop()
        print("✅ Scheduler stopped successfully.")


def list_personas():
    """List all available personas."""
    manager = PersonaManager()
    personas = manager.list_personas()
    
    print(f"\n{'='*60}")
    print(f"📋 Available Personas")
    print(f"{'='*60}")
    
    if not personas:
        print("   No personas found. Create one in data/personas/")
    else:
        for persona_id in personas:
            try:
                persona = manager.load_persona(persona_id)
                name = persona.get("basic_info", {}).get("name", "Unknown")
                niche = persona.get("basic_info", {}).get("niche", "Unknown")
                print(f"   • {persona_id}: {name} ({niche})")
            except Exception as e:
                print(f"   • {persona_id}: [Error loading: {e}]")
    
    print(f"{'='*60}\n")


def main():
    """Main function to run the Content Creation Engine."""
    parser = argparse.ArgumentParser(
        description="ContentCreationEngine - Automated Content Creation for Instagram Reels",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py run --persona sat_prep_guru
  python main.py run --persona sat_prep_guru --ideas 3 --skip-scraping
  python main.py schedule --persona sat_prep_guru --hour 8 --minute 0
  python main.py list-personas
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Run command
    run_parser = subparsers.add_parser("run", help="Run the content pipeline once")
    run_parser.add_argument(
        "--persona", "-p",
        required=True,
        help="Persona ID to use for content generation"
    )
    run_parser.add_argument(
        "--ideas", "-i",
        type=int,
        default=5,
        help="Number of content ideas to generate (default: 5)"
    )
    run_parser.add_argument(
        "--skip-scraping", "-s",
        action="store_true",
        help="Skip the scraping phase (for testing)"
    )
    
    # Schedule command
    schedule_parser = subparsers.add_parser("schedule", help="Start the daily scheduler")
    schedule_parser.add_argument(
        "--persona", "-p",
        required=True,
        help="Persona ID to use for content generation"
    )
    schedule_parser.add_argument(
        "--hour",
        type=int,
        default=8,
        help="Hour to run daily (24-hour format, default: 8)"
    )
    schedule_parser.add_argument(
        "--minute",
        type=int,
        default=0,
        help="Minute to run daily (default: 0)"
    )
    
    # List personas command
    subparsers.add_parser("list-personas", help="List all available personas")
    
    args = parser.parse_args()
    
    # Ensure directories exist
    settings.ensure_directories()
    
    if args.command == "run":
        run_pipeline(
            persona_id=args.persona,
            ideas_count=args.ideas,
            skip_scraping=args.skip_scraping
        )
    elif args.command == "schedule":
        start_scheduler(
            persona_id=args.persona,
            hour=args.hour,
            minute=args.minute
        )
    elif args.command == "list-personas":
        list_personas()
    else:
        # No command provided, show welcome message
        print(f"\n{'='*60}")
        print("🎬 ContentCreationEngine v0.1.0")
        print("   Automated Content Creation for Instagram Reels")
        print(f"{'='*60}")
        print("\nQuick Start:")
        print("  1. Copy .env.example to .env and add your API keys")
        print("  2. Create a persona in data/personas/ (see example_persona.json)")
        print("  3. Run: python main.py run --persona your_persona_id")
        print("\nFor more options, run: python main.py --help")
        print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
