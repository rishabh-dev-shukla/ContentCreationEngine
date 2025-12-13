"""
Flask Web Application for ContentCreationEngine.
Provides a web interface to manage personas, generate content, and view results.
"""

import sys
import json
import os
import logging
from pathlib import Path
from datetime import datetime
from functools import wraps
from threading import Thread

from flask import Flask, render_template, request, jsonify, redirect, url_for, flash

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import settings, Settings
from src.content_creation_engine.persona import PersonaManager
from src.content_creation_engine.scheduler import ContentPipeline
from src.content_creation_engine.scheduler.daily_workflow import ContentOutput

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__, 
            template_folder='templates',
            static_folder='static')
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key-change-in-production')

# Global state for tracking generation jobs
generation_jobs = {}


def get_persona_manager():
    """Get a PersonaManager instance."""
    return PersonaManager()


def get_all_content_outputs(persona_id: str = None) -> list:
    """Get all generated content outputs, optionally filtered by persona."""
    outputs = []
    output_dir = settings.output_dir
    
    if persona_id:
        persona_dirs = [output_dir / persona_id]
    else:
        persona_dirs = [d for d in output_dir.iterdir() if d.is_dir()]
    
    for persona_dir in persona_dirs:
        if not persona_dir.exists():
            continue
        for file_path in sorted(persona_dir.glob("*.json"), reverse=True):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    data['_file_path'] = str(file_path)
                    data['_filename'] = file_path.name
                    outputs.append(data)
            except Exception as e:
                logger.error(f"Error loading {file_path}: {e}")
    
    return outputs


def get_all_research_data() -> list:
    """Get all research data from cache."""
    research_data = []
    cache_dir = settings.research_cache_dir
    
    for file_path in sorted(cache_dir.glob("*.json"), reverse=True):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                research_data.append({
                    'date': file_path.stem.replace('_research', ''),
                    'filename': file_path.name,
                    'data': data
                })
        except Exception as e:
            logger.error(f"Error loading research {file_path}: {e}")
    
    return research_data


# =============================================================================
# Routes - Pages
# =============================================================================

@app.route('/')
def index():
    """Dashboard home page."""
    manager = get_persona_manager()
    personas = manager.list_personas()
    
    # Get recent content
    recent_content = get_all_content_outputs()[:5]
    
    # Get stats
    total_ideas = sum(len(c.get('content_ideas', [])) for c in recent_content)
    total_scripts = sum(len(c.get('scripts', [])) for c in recent_content)
    
    return render_template('index.html',
                          personas=personas,
                          recent_content=recent_content,
                          total_ideas=total_ideas,
                          total_scripts=total_scripts)


@app.route('/personas')
def personas_page():
    """Personas management page."""
    manager = get_persona_manager()
    persona_ids = manager.list_personas()
    
    personas = []
    for pid in persona_ids:
        try:
            persona = manager.load_persona(pid)
            personas.append(persona)
        except Exception as e:
            logger.error(f"Error loading persona {pid}: {e}")
    
    return render_template('personas.html', personas=personas)


@app.route('/personas/create')
def create_persona_page():
    """Create new persona page."""
    return render_template('persona_form.html', persona=None, edit_mode=False)


@app.route('/personas/<persona_id>/edit')
def edit_persona_page(persona_id):
    """Edit persona page."""
    manager = get_persona_manager()
    try:
        persona = manager.load_persona(persona_id)
        return render_template('persona_form.html', persona=persona, edit_mode=True)
    except FileNotFoundError:
        flash(f'Persona "{persona_id}" not found', 'error')
        return redirect(url_for('personas_page'))


@app.route('/generate')
def generate_page():
    """Content generation page."""
    manager = get_persona_manager()
    personas = manager.list_personas()
    
    # Available platforms
    platforms = ['Instagram', 'Reddit', 'News API', 'YouTube', 'Serper']
    
    # AI providers
    ai_providers = ['openai', 'deepseek', 'grok']
    current_provider = settings.ai.default_provider
    
    return render_template('generate.html',
                          personas=personas,
                          platforms=platforms,
                          ai_providers=ai_providers,
                          current_provider=current_provider)


@app.route('/content')
def content_page():
    """View generated content page."""
    manager = get_persona_manager()
    personas = manager.list_personas()
    
    # Get filter parameters
    selected_persona = request.args.get('persona', '')
    
    # Get content
    content_outputs = get_all_content_outputs(selected_persona if selected_persona else None)
    
    return render_template('content.html',
                          personas=personas,
                          selected_persona=selected_persona,
                          content_outputs=content_outputs)


@app.route('/content/<persona_id>/<filename>')
def view_content_detail(persona_id, filename):
    """View detailed content output."""
    file_path = settings.output_dir / persona_id / filename
    
    if not file_path.exists():
        flash('Content file not found', 'error')
        return redirect(url_for('content_page'))
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = json.load(f)
        return render_template('content_detail.html',
                              content=content,
                              persona_id=persona_id,
                              filename=filename)
    except Exception as e:
        flash(f'Error loading content: {e}', 'error')
        return redirect(url_for('content_page'))


@app.route('/research')
def research_page():
    """View research data page."""
    research_data = get_all_research_data()
    return render_template('research.html', research_data=research_data)


@app.route('/settings')
def settings_page():
    """Settings page for API keys and configurations."""
    # Get current settings (mask API keys)
    current_settings = {
        'ai': {
            'openai_api_key': '***' + (settings.ai.openai_api_key[-4:] if settings.ai.openai_api_key else ''),
            'deepseek_api_key': '***' + (settings.ai.deepseek_api_key[-4:] if settings.ai.deepseek_api_key else ''),
            'grok_api_key': '***' + (settings.ai.grok_api_key[-4:] if settings.ai.grok_api_key else ''),
            'default_provider': settings.ai.default_provider,
            'openai_model': settings.ai.openai_model,
            'deepseek_model': settings.ai.deepseek_model,
            'grok_model': settings.ai.grok_model,
        },
        'instagram': {
            'access_token': '***' + (settings.instagram.access_token[-4:] if settings.instagram.access_token else ''),
            'business_account_id': settings.instagram.business_account_id or '',
        },
        'reddit': {
            'client_id': settings.reddit.client_id or '',
            'client_secret': '***' + (settings.reddit.client_secret[-4:] if settings.reddit.client_secret else ''),
        },
        'news': {
            'api_key': '***' + (settings.news.api_key[-4:] if settings.news.api_key else ''),
        },
        'youtube': {
            'api_key': '***' + (settings.youtube.api_key[-4:] if settings.youtube.api_key else ''),
        },
        'serper': {
            'api_key': '***' + (settings.serper.api_key[-4:] if settings.serper.api_key else ''),
        },
        'content': {
            'ideas_per_day': settings.content.ideas_per_day,
            'script_min_words': settings.content.script_min_words,
            'script_max_words': settings.content.script_max_words,
        }
    }
    
    return render_template('settings.html', settings=current_settings)


# =============================================================================
# Routes - API
# =============================================================================

@app.route('/api/personas', methods=['GET'])
def api_list_personas():
    """API: List all personas."""
    manager = get_persona_manager()
    persona_ids = manager.list_personas()
    
    personas = []
    for pid in persona_ids:
        try:
            persona = manager.load_persona(pid)
            personas.append({
                'persona_id': pid,
                'name': persona.get('basic_info', {}).get('name', 'Unknown'),
                'niche': persona.get('basic_info', {}).get('niche', 'Unknown'),
                'target_audience': persona.get('basic_info', {}).get('target_audience', ''),
            })
        except Exception:
            pass
    
    return jsonify({'personas': personas})


@app.route('/api/personas', methods=['POST'])
def api_create_persona():
    """API: Create a new persona."""
    data = request.json
    
    required_fields = ['persona_id', 'name', 'niche', 'target_audience']
    for field in required_fields:
        if not data.get(field):
            return jsonify({'error': f'Missing required field: {field}'}), 400
    
    manager = get_persona_manager()
    
    # Check if persona already exists
    if data['persona_id'] in manager.list_personas():
        return jsonify({'error': 'Persona ID already exists'}), 400
    
    try:
        persona = manager.create_persona(
            persona_id=data['persona_id'],
            name=data['name'],
            niche=data['niche'],
            target_audience=data['target_audience'],
            tone=data.get('tone', 'Friendly and engaging'),
            unique_angle=data.get('unique_angle', ''),
            hashtags=data.get('hashtags', []),
            posting_frequency=data.get('posting_frequency', 'daily'),
            hook_style=data.get('hook_style', 'Question or bold statement'),
            content_style=data.get('content_style', 'Fast-paced, value-packed'),
            cta_style=data.get('cta_style', 'Save and share focused'),
            avoid=data.get('avoid', []),
        )
        manager.save_persona(persona)
        return jsonify({'success': True, 'persona_id': data['persona_id']})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/personas/<persona_id>', methods=['GET'])
def api_get_persona(persona_id):
    """API: Get a specific persona."""
    manager = get_persona_manager()
    try:
        persona = manager.load_persona(persona_id)
        return jsonify(persona)
    except FileNotFoundError:
        return jsonify({'error': 'Persona not found'}), 404


@app.route('/api/personas/<persona_id>', methods=['PUT'])
def api_update_persona(persona_id):
    """API: Update a persona."""
    data = request.json
    manager = get_persona_manager()
    
    try:
        # Load existing persona
        persona = manager.load_persona(persona_id)
        
        # Update basic info
        if 'basic_info' in data:
            persona['basic_info'].update(data['basic_info'])
        
        # Update style guide
        if 'style_guide' in data:
            persona['style_guide'].update(data['style_guide'])
        
        # Update other fields
        for key in ['content_preferences', 'learned_patterns']:
            if key in data:
                persona[key] = data[key]
        
        manager.save_persona(persona)
        return jsonify({'success': True})
    except FileNotFoundError:
        return jsonify({'error': 'Persona not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/personas/<persona_id>', methods=['DELETE'])
def api_delete_persona(persona_id):
    """API: Delete a persona."""
    manager = get_persona_manager()
    
    file_path = manager.personas_dir / f"{persona_id}.json"
    if not file_path.exists():
        return jsonify({'error': 'Persona not found'}), 404
    
    try:
        file_path.unlink()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/generate', methods=['POST'])
def api_generate_content():
    """API: Start content generation."""
    data = request.json
    
    persona_id = data.get('persona_id')
    if not persona_id:
        return jsonify({'error': 'Missing persona_id'}), 400
    
    ideas_count = data.get('ideas_count', 5)
    skip_scraping = data.get('skip_scraping', False)
    platforms = data.get('platforms', [])
    ai_provider = data.get('ai_provider', settings.ai.default_provider)
    
    # Create a unique job ID
    job_id = f"{persona_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # Mark job as running
    generation_jobs[job_id] = {
        'status': 'running',
        'persona_id': persona_id,
        'started_at': datetime.now().isoformat(),
        'progress': 0,
        'message': 'Starting content generation...'
    }
    
    def run_generation():
        try:
            # Update AI provider temporarily if different
            original_provider = settings.ai.default_provider
            if ai_provider != original_provider:
                settings.ai.default_provider = ai_provider
            
            pipeline = ContentPipeline()
            generation_jobs[job_id]['message'] = 'Running content pipeline...'
            generation_jobs[job_id]['progress'] = 25
            
            output = pipeline.run(
                persona_id=persona_id,
                ideas_count=ideas_count,
                skip_scraping=skip_scraping
            )
            
            generation_jobs[job_id]['status'] = 'completed'
            generation_jobs[job_id]['progress'] = 100
            generation_jobs[job_id]['message'] = 'Content generation completed!'
            generation_jobs[job_id]['result'] = {
                'ideas_count': len(output.ideas),
                'scripts_count': len(output.scripts),
                'visuals_count': len(output.visuals),
                'output_file': output.metadata.get('output_file', '')
            }
            
            # Restore original provider
            if ai_provider != original_provider:
                settings.ai.default_provider = original_provider
                
        except Exception as e:
            logger.error(f"Generation error: {e}")
            generation_jobs[job_id]['status'] = 'failed'
            generation_jobs[job_id]['message'] = str(e)
    
    # Run in background thread
    thread = Thread(target=run_generation)
    thread.start()
    
    return jsonify({'job_id': job_id, 'status': 'started'})


@app.route('/api/generate/<job_id>/status', methods=['GET'])
def api_generation_status(job_id):
    """API: Get generation job status."""
    if job_id not in generation_jobs:
        return jsonify({'error': 'Job not found'}), 404
    
    return jsonify(generation_jobs[job_id])


@app.route('/api/content', methods=['GET'])
def api_list_content():
    """API: List all generated content."""
    persona_id = request.args.get('persona_id')
    content_outputs = get_all_content_outputs(persona_id)
    
    # Simplify for API response
    simplified = []
    for output in content_outputs:
        simplified.append({
            'date': output.get('date'),
            'persona_id': output.get('persona_id'),
            'niche': output.get('niche'),
            'ideas_count': len(output.get('content_ideas', [])),
            'scripts_count': len(output.get('scripts', [])),
            'filename': output.get('_filename')
        })
    
    return jsonify({'content': simplified})


@app.route('/api/content/<persona_id>/<filename>', methods=['GET'])
def api_get_content(persona_id, filename):
    """API: Get specific content output."""
    file_path = settings.output_dir / persona_id / filename
    
    if not file_path.exists():
        return jsonify({'error': 'Content not found'}), 404
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = json.load(f)
        return jsonify(content)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/content/<persona_id>/<filename>/idea/<int:idea_index>', methods=['PUT'])
def api_update_idea(persona_id, filename, idea_index):
    """API: Update a specific idea (edit/approve/reject)."""
    file_path = settings.output_dir / persona_id / filename
    
    if not file_path.exists():
        return jsonify({'error': 'Content not found'}), 404
    
    data = request.json
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = json.load(f)
        
        ideas = content.get('content_ideas', [])
        if idea_index < 0 or idea_index >= len(ideas):
            return jsonify({'error': 'Invalid idea index'}), 400
        
        # Update the idea - handle all possible fields
        updatable_fields = ['status', 'title', 'description', 'hook', 
                          'content_structure', 'hashtags']
        
        for field in updatable_fields:
            if field in data:
                ideas[idea_index][field] = data[field]
        
        # Track when it was last edited
        ideas[idea_index]['last_edited'] = datetime.now().isoformat()
        
        content['content_ideas'] = ideas
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(content, f, indent=2, ensure_ascii=False)
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/content/<persona_id>/<filename>/script/<int:script_index>', methods=['PUT'])
def api_update_script(persona_id, filename, script_index):
    """API: Update a specific script."""
    file_path = settings.output_dir / persona_id / filename
    
    if not file_path.exists():
        return jsonify({'error': 'Content not found'}), 404
    
    data = request.json
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = json.load(f)
        
        scripts = content.get('scripts', [])
        if script_index < 0 or script_index >= len(scripts):
            return jsonify({'error': 'Invalid script index'}), 400
        
        # Update the script - handle all possible fields
        updatable_fields = ['status', 'title', 'hook', 'cta', 'speaker_notes', 
                          'full_script', 'main_content', 'script', 'content']
        
        for field in updatable_fields:
            if field in data:
                scripts[script_index][field] = data[field]
        
        # Track when it was last edited
        scripts[script_index]['last_edited'] = datetime.now().isoformat()
        
        content['scripts'] = scripts
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(content, f, indent=2, ensure_ascii=False)
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/research', methods=['GET'])
def api_list_research():
    """API: List all research data."""
    research_data = get_all_research_data()
    return jsonify({'research': research_data})


@app.route('/api/settings', methods=['GET'])
def api_get_settings():
    """API: Get current settings (masked)."""
    return jsonify({
        'ai_provider': settings.ai.default_provider,
        'ideas_per_day': settings.content.ideas_per_day,
    })


@app.route('/api/settings/env', methods=['POST'])
def api_update_env():
    """API: Update .env file with new settings."""
    data = request.json
    env_path = PROJECT_ROOT / '.env'
    
    # Read existing .env
    env_vars = {}
    if env_path.exists():
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key] = value
    
    # Update with new values
    for key, value in data.items():
        if value:  # Only update non-empty values
            env_vars[key] = value
    
    # Write back
    try:
        with open(env_path, 'w') as f:
            for key, value in env_vars.items():
                f.write(f"{key}={value}\n")
        
        return jsonify({'success': True, 'message': 'Settings saved. Restart the app to apply changes.'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# =============================================================================
# Error Handlers
# =============================================================================

@app.errorhandler(404)
def not_found(e):
    return render_template('404.html'), 404


@app.errorhandler(500)
def server_error(e):
    return render_template('500.html'), 500


# =============================================================================
# Main
# =============================================================================

def create_app():
    """Create and configure the Flask app."""
    settings.ensure_directories()
    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=5000)
