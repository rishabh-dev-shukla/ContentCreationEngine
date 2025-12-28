"""
Flask Web Application for ContentCreationEngine.
Provides a web interface to manage personas, generate content, and view results.
"""

import sys
import json
import os
import logging
from pathlib import Path
from datetime import datetime, timedelta
from functools import wraps
from threading import Thread

from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session, g

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import settings, Settings
from src.content_creation_engine.persona import PersonaManager
from src.content_creation_engine.scheduler import ContentPipeline
from src.content_creation_engine.scheduler.daily_workflow import ContentOutput
from src.content_creation_engine.generators import InsightsAnalyzer
from web.auth import (
    login_required, admin_required, get_current_user, get_current_customer_id,
    set_current_customer, verify_firebase_token, login_user, logout_user, get_user_customers
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__, 
            template_folder='templates',
            static_folder='static')
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key-change-in-production')
app.permanent_session_lifetime = timedelta(days=7)

# Firebase configuration for client-side SDK
FIREBASE_CONFIG = {
    'apiKey': os.getenv('FIREBASE_API_KEY', ''),
    'authDomain': os.getenv('FIREBASE_AUTH_DOMAIN', ''),
    'projectId': os.getenv('FIREBASE_PROJECT_ID', 'content-engine-8be02'),
    'storageBucket': os.getenv('FIREBASE_STORAGE_BUCKET', ''),
    'messagingSenderId': os.getenv('FIREBASE_MESSAGING_SENDER_ID', ''),
    'appId': os.getenv('FIREBASE_APP_ID', '')
}

# Global state for tracking generation jobs (in-memory fallback)
generation_jobs = {}
insights_jobs = {}
video_jobs = {}

# Persistent job tracking directory
JOBS_DIR = Path(settings.output_dir) / '.jobs'
JOBS_DIR.mkdir(exist_ok=True)

def save_job_status(job_id, job_data):
    """Save job status to filesystem for persistence across worker restarts."""
    try:
        job_file = JOBS_DIR / f"{job_id}.json"
        with open(job_file, 'w') as f:
            json.dump(job_data, f)
    except Exception as e:
        logger.error(f"Failed to save job status: {e}")

def load_job_status(job_id):
    """Load job status from filesystem."""
    try:
        job_file = JOBS_DIR / f"{job_id}.json"
        if job_file.exists():
            with open(job_file, 'r') as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load job status: {e}")
    return None

def get_job_status(job_id):
    """Get job status from memory or filesystem."""
    # Try memory first
    if job_id in video_jobs:
        return video_jobs[job_id]
    # Fall back to filesystem
    return load_job_status(job_id)

def update_job_status(job_id, updates):
    """Update job status in both memory and filesystem."""
    # Update memory
    if job_id not in video_jobs:
        video_jobs[job_id] = {}
    video_jobs[job_id].update(updates)
    # Save to filesystem
    save_job_status(job_id, video_jobs[job_id])

# Log application startup
import time
APP_START_TIME = time.time()
APP_START_ID = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
logger.info(f"=== APPLICATION STARTED === ID: {APP_START_ID}, Time: {datetime.now()}")
logger.info(f"Worker PID: {os.getpid()}")


# =============================================================================
# Context Processor - Make auth info available to all templates
# =============================================================================

@app.context_processor
def inject_auth():
    """Inject authentication info into all templates."""
    user = get_current_user()
    customer_id = get_current_customer_id()
    customers = get_user_customers() if user else []
    return {
        'current_user': user,
        'current_customer_id': customer_id,
        'user_customers': customers
    }


def get_persona_manager(customer_id: str = None):
    """
    Get a PersonaManager instance.
    Uses Firebase if a customer_id is provided, otherwise falls back to local files.
    """
    from src.content_creation_engine.persona import get_persona_manager as get_pm
    
    # Try to get customer_id from session if not provided
    if not customer_id:
        customer_id = get_current_customer_id()
    
    if customer_id:
        return get_pm(customer_id=customer_id, use_firebase=True)
    
    # Fall back to local PersonaManager
    return PersonaManager()


def get_all_content_outputs(persona_id: str = None) -> list:
    """Get all generated content outputs, optionally filtered by persona."""
    customer_id = get_current_customer_id()
    
    # If we have a customer context, use Firebase
    if customer_id:
        from src.content_creation_engine.utils.firebase_service import get_firebase_service
        firebase = get_firebase_service()
        if firebase:
            try:
                outputs = firebase.list_content_outputs(
                    customer_id=customer_id,
                    persona_id=persona_id,
                    limit=100
                )
                return outputs
            except Exception as e:
                logger.error(f"Error getting content from Firebase: {e}")
                return []
    
    # Fallback to local files
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
    customer_id = get_current_customer_id()
    
    # If we have a customer context, use Firebase
    if customer_id:
        from src.content_creation_engine.utils.firebase_service import get_firebase_service
        firebase = get_firebase_service()
        if firebase:
            try:
                research_list = firebase.list_research(customer_id=customer_id, limit=50)
                # Transform to match the expected format
                # Firebase research docs have the data at root level, not nested under 'data'
                result = []
                for r in research_list:
                    doc_id = r.get('_id', '')
                    # Extract date from doc_id (e.g., "2025-12-14_research" -> "2025-12-14")
                    date = doc_id.replace('_research', '') if doc_id else r.get('saved_at', '')[:10]
                    # The research data is at root level, minus metadata fields
                    data = {k: v for k, v in r.items() if not k.startswith('_') and k not in ['saved_at', 'migrated_from', 'migrated_at']}
                    result.append({
                        'date': date,
                        'filename': f"{date}_research.json",
                        'data': data
                    })
                return result
            except Exception as e:
                logger.error(f"Error getting research from Firebase: {e}")
                return []
    
    # Fallback to local files
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


def get_all_insights(persona_id: str = None) -> list:
    """Get all insights, optionally filtered by persona."""
    customer_id = get_current_customer_id()
    
    # If we have a customer context, use Firebase
    if customer_id:
        from src.content_creation_engine.utils.firebase_service import get_firebase_service
        firebase = get_firebase_service()
        if firebase:
            try:
                insights_list = firebase.list_insights(
                    customer_id=customer_id,
                    persona_id=persona_id,
                    limit=50
                )
                # Transform to match expected format
                for insight in insights_list:
                    # Add _filename for compatibility with templates
                    if '_id' in insight and '_filename' not in insight:
                        insight['_filename'] = f"{insight['_id']}.json"
                return insights_list
            except Exception as e:
                logger.error(f"Error getting insights from Firebase: {e}")
                return []
    
    # Fallback to local InsightsAnalyzer
    analyzer = InsightsAnalyzer()
    return analyzer.list_insights(persona_id)


# =============================================================================
# Routes - Authentication
# =============================================================================

@app.route('/login')
def login_page():
    """Login page."""
    # If already logged in, redirect to dashboard
    if get_current_user():
        return redirect(url_for('index'))
    
    return render_template('login.html', firebase_config=json.dumps(FIREBASE_CONFIG))


@app.route('/logout')
def logout():
    """Logout and redirect to login page."""
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login_page'))


@app.route('/switch-customer/<customer_id>')
@login_required
def switch_customer(customer_id):
    """Switch the current customer context."""
    user = get_current_user()
    
    # Verify user has access to this customer
    if customer_id not in user.get('customers', []):
        flash('You do not have access to this customer.', 'error')
        return redirect(url_for('index'))
    
    set_current_customer(customer_id)
    flash(f'Switched to customer: {customer_id}', 'success')
    return redirect(url_for('index'))


@app.route('/api/auth/verify', methods=['POST'])
def api_verify_auth():
    """API: Verify Firebase ID token and create session."""
    data = request.json
    id_token = data.get('id_token')
    
    if not id_token:
        return jsonify({'success': False, 'error': 'Missing ID token'}), 400
    
    # Verify token and get user data
    user_data = verify_firebase_token(id_token)
    
    if not user_data:
        return jsonify({
            'success': False, 
            'error': 'User not authorized. Please contact your administrator.'
        }), 401
    
    # Log the user in
    login_user(user_data)
    
    return jsonify({
        'success': True,
        'user': {
            'email': user_data.get('email'),
            'name': user_data.get('name'),
            'role': user_data.get('role')
        },
        'redirect': url_for('index')
    })


# =============================================================================
# Routes - Pages
# =============================================================================

@app.route('/')
@login_required
def index():
    """Dashboard home page."""
    manager = get_persona_manager()
    personas = manager.list_personas()
    
    # Get all content for stats
    all_content = get_all_content_outputs()
    recent_content = all_content[:5]
    
    # Get stats from ALL content
    total_ideas = sum(len(c.get('content_ideas', [])) for c in all_content)
    total_scripts = sum(len(c.get('scripts', [])) for c in all_content)
    
    # Get research data count
    research_data = get_all_research_data()
    
    # Get insights count
    all_insights = get_all_insights()
    
    return render_template('index.html',
                          personas=personas,
                          recent_content=recent_content,
                          total_ideas=total_ideas,
                          total_scripts=total_scripts,
                          research_count=len(research_data),
                          insights_count=len(all_insights))


# Scripts page for a persona
@app.route("/scripts")
@app.route("/scripts/<persona_id>")
@login_required
def scripts_page(persona_id=None):
    from flask import request
    manager = get_persona_manager()
    personas = manager.list_personas()
    
    # Default to first persona if none selected
    if not persona_id and personas:
        persona_id = personas[0]
    
    status = request.args.get("status", "all")
    view = request.args.get("view", "table")
    
    # Gather all scripts for this persona
    scripts = []
    if persona_id:
        outputs = get_all_content_outputs(persona_id=persona_id)
        for content in outputs:
            filename = content.get("_filename")
            for idx, script in enumerate(content.get("scripts", [])):
                s = dict(script)
                s["filename"] = filename
                s["index"] = idx
                scripts.append(s)
        # Filter by status
        if status in ("approved", "rejected"):
            scripts = [s for s in scripts if s.get("status") == status]
        # Sort by most recent (if possible)
        scripts = sorted(scripts, key=lambda s: s.get("last_edited") or s.get("created_at") or "", reverse=True)
    
    return render_template(
        "scripts.html",
        personas=personas,
        persona_id=persona_id,
        scripts=scripts,
        status=status,
        view=view
    )


@app.route('/personas')
@login_required
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
@login_required
def create_persona_page():
    """Create new persona page."""
    return render_template('persona_form.html', persona=None, edit_mode=False)


@app.route('/personas/<persona_id>/edit')
@login_required
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
@login_required
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
@login_required
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
@login_required
def view_content_detail(persona_id, filename):
    """View detailed content output."""
    customer_id = get_current_customer_id()
    
    # Try Firebase first if customer is logged in
    if customer_id:
        from src.content_creation_engine.utils.firebase_service import get_firebase_service
        firebase = get_firebase_service()
        if firebase:
            try:
                # The filename from Firebase is the document ID
                output_id = filename.replace('.json', '') if filename.endswith('.json') else filename
                content = firebase.get_content_output(customer_id, persona_id, output_id)
                if content:
                    return render_template('content_detail.html',
                                          content=content,
                                          persona_id=persona_id,
                                          filename=filename)
            except Exception as e:
                logger.error(f"Error loading content from Firebase: {e}")
    
    # Fallback to local files
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
@login_required
def research_page():
    """View research data page."""
    research_data = get_all_research_data()
    return render_template('research.html', research_data=research_data)


@app.route('/insights')
@login_required
def insights_page():
    """View insights page."""
    manager = get_persona_manager()
    personas = manager.list_personas()
    
    # Get all insights
    all_insights = get_all_insights()
    
    # Get all research runs with metadata
    research_runs = []
    for research in get_all_research_data():
        source_count = sum(
            len(v) if isinstance(v, list) else 0 
            for v in research.get('data', {}).values()
        )
        research_runs.append({
            'date': research['date'],
            'filename': research['filename'],
            'source_count': source_count
        })
    
    return render_template('insights.html', 
                          personas=personas, 
                          insights_list=all_insights,
                          research_runs=research_runs)


@app.route('/insights/<persona_id>/<filename>')
@login_required
def view_insights_detail(persona_id, filename):
    """View detailed insights."""
    customer_id = get_current_customer_id()
    
    # Try Firebase first if we have a customer context
    if customer_id:
        from src.content_creation_engine.utils.firebase_service import get_firebase_service
        firebase = get_firebase_service()
        if firebase:
            try:
                # Extract insights_id from filename (remove .json extension)
                insights_id = filename.replace('.json', '')
                insights = firebase.get_insights(customer_id, persona_id, insights_id)
                if insights:
                    return render_template('insights_detail.html',
                                          insights=insights,
                                          persona_id=persona_id,
                                          filename=filename)
            except Exception as e:
                logger.error(f"Error loading insights from Firebase: {e}")
    
    # Fallback to local file
    insights_dir = settings.output_dir / "insights" / persona_id
    file_path = insights_dir / filename
    
    if not file_path.exists():
        flash('Insights file not found', 'error')
        return redirect(url_for('insights_page'))
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            insights = json.load(f)
        return render_template('insights_detail.html',
                              insights=insights,
                              persona_id=persona_id,
                              filename=filename)
    except Exception as e:
        flash(f'Error loading insights: {e}', 'error')
        return redirect(url_for('insights_page'))


@app.route('/settings')
@login_required
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
@login_required
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
@login_required
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
@login_required
def api_get_persona(persona_id):
    """API: Get a specific persona."""
    manager = get_persona_manager()
    try:
        persona = manager.load_persona(persona_id)
        return jsonify(persona)
    except FileNotFoundError:
        return jsonify({'error': 'Persona not found'}), 404


@app.route('/api/personas/<persona_id>', methods=['PUT'])
@login_required
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
@login_required
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
@login_required
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
@login_required
def api_generation_status(job_id):
    """API: Get generation job status."""
    if job_id not in generation_jobs:
        return jsonify({'error': 'Job not found'}), 404
    
    return jsonify(generation_jobs[job_id])


# =============================================================================
# API Routes - Insights
# =============================================================================

@app.route('/api/insights/research-runs', methods=['GET'])
@login_required
def api_get_research_runs():
    """API: Get research runs for a specific persona."""
    persona_id = request.args.get('persona_id')
    if not persona_id:
        return jsonify({'error': 'Missing persona_id'}), 400
    
    # Get all research runs
    research_runs = []
    for research in get_all_research_data():
        source_count = sum(
            len(v) if isinstance(v, list) else 0 
            for v in research.get('data', {}).values()
        )
        research_runs.append({
            'date': research['date'],
            'filename': research['filename'],
            'source_count': source_count
        })
    
    return jsonify(research_runs)

@app.route('/api/insights/generate', methods=['POST'])
@login_required
def api_generate_insights():
    """API: Start insights analysis."""
    data = request.json
    
    persona_id = data.get('persona_id')
    if not persona_id:
        return jsonify({'error': 'Missing persona_id'}), 400
    
    research_file = data.get('research_file')
    if not research_file:
        return jsonify({'error': 'Missing research_file'}), 400
    
    analysis_types = data.get('analysis_types', None)  # None means all types
    
    # Create a unique job ID
    job_id = f"insights_{persona_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # Mark job as running
    insights_jobs[job_id] = {
        'status': 'running',
        'persona_id': persona_id,
        'started_at': datetime.now().isoformat(),
        'progress': 0,
        'message': 'Starting insights analysis...'
    }
    
    def run_analysis():
        try:
            manager = get_persona_manager()
            persona = manager.load_persona(persona_id)
            
            if not persona:
                insights_jobs[job_id]['status'] = 'failed'
                insights_jobs[job_id]['message'] = f'Persona {persona_id} not found'
                return
            
            insights_jobs[job_id]['message'] = 'Loading research data...'
            insights_jobs[job_id]['progress'] = 10
            
            # Load selected research file
            research_data = {}
            research_file_path = settings.research_cache_dir / research_file
            if research_file_path.exists():
                try:
                    with open(research_file_path, 'r', encoding='utf-8') as f:
                        research_data = json.load(f)
                except Exception as e:
                    logger.error(f"Error loading research file: {e}")
            
            if not research_data:
                insights_jobs[job_id]['status'] = 'failed'
                insights_jobs[job_id]['message'] = 'No research data available. Run research first.'
                return
            
            insights_jobs[job_id]['message'] = 'Analyzing research data...'
            insights_jobs[job_id]['progress'] = 25
            
            analyzer = InsightsAnalyzer()
            insights = analyzer.analyze_research_data(
                research_data=research_data,
                persona=persona,
                analysis_types=analysis_types
            )
            
            insights_jobs[job_id]['message'] = 'Saving insights...'
            insights_jobs[job_id]['progress'] = 90
            
            output_file = analyzer.save_insights(insights, persona_id)
            
            insights_jobs[job_id]['status'] = 'completed'
            insights_jobs[job_id]['progress'] = 100
            insights_jobs[job_id]['message'] = 'Insights analysis completed!'
            insights_jobs[job_id]['result'] = {
                'output_file': str(output_file),
                'filename': output_file.name,
                'analyses_count': len(insights.get('analyses', {}))
            }
            
        except Exception as e:
            logger.error(f"Insights generation error: {e}")
            insights_jobs[job_id]['status'] = 'failed'
            insights_jobs[job_id]['message'] = str(e)
    
    # Run in background thread
    thread = Thread(target=run_analysis)
    thread.start()
    
    return jsonify({'job_id': job_id, 'status': 'started'})


@app.route('/api/insights/<job_id>/status', methods=['GET'])
@login_required
def api_insights_status(job_id):
    """API: Get insights job status."""
    if job_id not in insights_jobs:
        return jsonify({'error': 'Job not found'}), 404
    
    return jsonify(insights_jobs[job_id])


@app.route('/api/insights', methods=['GET'])
@login_required
def api_list_insights():
    """API: List all insights."""
    persona_id = request.args.get('persona_id')
    insights_list = get_all_insights(persona_id)
    
    # Simplify for API response
    simplified = []
    for insight in insights_list:
        simplified.append({
            'generated_at': insight.get('generated_at'),
            'persona_id': insight.get('persona_id'),
            'niche': insight.get('niche'),
            'analyses_count': len(insight.get('analyses', {})),
            'filename': insight.get('_filename')
        })
    
    return jsonify({'insights': simplified})


@app.route('/api/content', methods=['GET'])
@login_required
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
@login_required
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
@login_required
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
@login_required
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
@login_required
def api_list_research():
    """API: List all research data."""
    research_data = get_all_research_data()
    return jsonify({'research': research_data})


@app.route('/api/settings', methods=['GET'])
@login_required
def api_get_settings():
    """API: Get current settings (masked)."""
    return jsonify({
        'ai_provider': settings.ai.default_provider,
        'ideas_per_day': settings.content.ideas_per_day,
    })


@app.route('/api/settings/env', methods=['POST'])
@login_required
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
# Routes - Video Generator
# =============================================================================

# Default output directory for video generation
VIDEO_OUTPUT_DIR = settings.output_dir / "video_outputs"

# Store video generation jobs
video_generation_jobs = {}


def get_recent_videos() -> list:
    """Get list of recently generated videos."""
    videos = []
    video_dir = VIDEO_OUTPUT_DIR
    
    # Get videos from Firebase (persistent) and local job files
    customer_id = get_current_customer_id()
    
    # First, try to get from Firebase
    if customer_id:
        from src.content_creation_engine.utils.firebase_service import get_firebase_service
        firebase = get_firebase_service()
        if firebase:
            try:
                videos = firebase.list_video_jobs(customer_id, limit=10)
                if videos:
                    return videos
            except Exception as e:
                logger.error(f"Error getting videos from Firebase: {e}")
    
    # Fallback: Get from local job files
    jobs_dir = JOBS_DIR
    if jobs_dir.exists():
        for job_file in sorted(jobs_dir.glob("video_*.json"), reverse=True):
            try:
                with open(job_file, 'r') as f:
                    job_data = json.load(f)
                    videos.append({
                        'job_id': job_file.stem,
                        'created_at': job_data.get('started_at', ''),
                        'problem': job_data.get('problem', 'Unknown'),
                        'status': job_data.get('status', 'unknown')
                    })
            except:
                pass
    
    return videos[:10]  # Return only the 10 most recent


@app.route('/video-generator')
@login_required
def video_generator_page():
    """Video generator page."""
    default_output_dir = str(VIDEO_OUTPUT_DIR)
    recent_videos = get_recent_videos()
    
    return render_template('video_generator.html',
                          default_output_dir=default_output_dir,
                          recent_videos=recent_videos)


def _generate_video_background(job_id, problem_statement, background_color, api_type, 
                                video_quality, output_dir, patch_width, patch_height, patch_position):
    """Background task for video generation."""
    logger.info(f"=== Background thread started for job: {job_id} ===")
    logger.info(f"video_jobs at thread start: {list(video_jobs.keys())}")
    
    try:
        # Convert hex color to RGB tuple for watermark patch
        def hex_to_rgb(hex_color):
            hex_color = hex_color.lstrip('#')
            return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        
        try:
            patch_color = hex_to_rgb(background_color)
        except:
            patch_color = (255, 255, 255)  # Default to white
        
        # Import video generation modules
        from video_gen.math_ai_video_generator import generate_math_ai_video
        from video_gen.process_video import remove_watermark_with_patch
        import time
        
        # Step 1: Generate video using Knolify API
        update_job_status(job_id, {'message': 'Sending request to Knolify API...', 'progress': 10})
        logger.info(f"Generating video for problem: {problem_statement[:50]}...")
        
        try:
            result = generate_math_ai_video(
                math_problem=problem_statement,
                api_type=api_type,
                background_color=background_color,
                quality=video_quality,
                remove_watermark=False  # We'll process manually
            )
        except Exception as knolify_error:
            logger.error(f"Knolify API error: {knolify_error}")
            raise Exception(f"Knolify API failed: {str(knolify_error)}")
        
        video_url = result.get('video_link')
        if not video_url:
            raise Exception("No video URL returned from Knolify API")
        
        # Step 2: Create output directory with timestamp
        update_job_status(job_id, {'message': 'Video generated! Processing watermark removal...', 'progress': 60})
        
        timestamp = int(time.time())
        output_folder = Path(output_dir) / f"video_{timestamp}"
        output_folder.mkdir(parents=True, exist_ok=True)
        output_path = output_folder / "video_processed.mp4"
        
        # Step 3: Remove watermark with patch
        logger.info(f"Removing watermark with {patch_color} patch...")
        processed_video = remove_watermark_with_patch(
            video_input=video_url,
            output_path=str(output_path),
            patch_width=patch_width,
            patch_height=patch_height,
            patch_color=patch_color,
            position=patch_position,
            margin_x=0,
            margin_y=0
        )
        
        # Step 4: Save metadata
        update_job_status(job_id, {'message': 'Saving metadata...', 'progress': 90})
        
        metadata = {
            'problem': problem_statement,
            'background_color': background_color,
            'api_type': api_type,
            'video_quality': video_quality,
            'original_url': video_url,
            'vtt_file': result.get('vtt_file'),
            'srt_file': result.get('srt_file'),
            'processed_video': str(processed_video),
            'created_at': datetime.now().isoformat()
        }
        
        metadata_path = output_folder / 'metadata.json'
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2)
        
        logger.info(f"Video processing complete: {processed_video}")
        
        # Update job status
        update_job_status(job_id, {
            'status': 'completed',
            'progress': 100,
            'message': 'Video generation completed!',
            'problem': problem_statement,
            'result': {
                'processed_video': str(processed_video),
                'output_folder': str(output_folder)
            }
        })
        
        # Save to Firebase for persistence across server restarts
        try:
            from src.content_creation_engine.utils.firebase_service import get_firebase_service
            firebase = get_firebase_service()
            job_data = get_job_status(job_id)
            customer_id = job_data.get('customer_id') if job_data else None
            if firebase and customer_id:
                firebase.save_video_job(customer_id, job_id, {
                    'job_id': job_id,
                    'status': 'completed',
                    'problem': problem_statement,
                    'created_at': datetime.now().isoformat(),
                    'background_color': background_color,
                    'api_type': api_type,
                    'video_quality': video_quality
                })
                logger.info(f"Saved video job {job_id} to Firebase")
        except Exception as fb_error:
            logger.error(f"Failed to save video job to Firebase: {fb_error}")
        
    except Exception as e:
        logger.error(f"Video generation error for job {job_id}: {e}")
        import traceback
        logger.error(f"Full traceback:\n{traceback.format_exc()}")
        
        # Defensive update - check if job still exists
        try:
            current_job = get_job_status(job_id)
            if current_job:
                update_job_status(job_id, {
                    'status': 'failed',
                    'progress': 0,
                    'message': f'Error: {str(e)}'
                })
                logger.info(f"Updated job {job_id} to failed status")
            else:
                # Job disappeared! Recreate it with error status
                logger.error(f"Job {job_id} not found! Creating with error status")
                update_job_status(job_id, {
                    'status': 'failed',
                    'progress': 0,
                    'message': f'Error: {str(e)}',
                    'started_at': datetime.now().isoformat()
                })
        except Exception as update_error:
            logger.error(f"Failed to update job status: {update_error}")
    
    finally:
        # Ensure job exists with final status
        logger.info(f"Background thread finishing for job {job_id}")
        logger.info(f"Final video_jobs state: {list(video_jobs.keys())}")
        if job_id in video_jobs:
            logger.info(f"Job {job_id} final status: {video_jobs[job_id].get('status')}")
        else:
            logger.error(f"Job {job_id} missing from video_jobs at thread end!")


@app.route('/api/video/generate', methods=['POST'])
@login_required
def api_generate_video():
    """API: Start video generation in background."""
    logger.info("=== Video generation endpoint called ===")
    logger.info(f"App start ID: {APP_START_ID}, PID: {os.getpid()}, Uptime: {time.time() - APP_START_TIME:.1f}s")
    logger.info(f"Current video_jobs before creation: {list(video_jobs.keys())}")
    
    data = request.json
    
    # Extract parameters
    problem_statement = data.get('problem_statement', '').strip()
    background_color = data.get('background_color', '#FFFFFF')
    api_type = data.get('api_type', 'prism')  # 'prism' or 'grant'
    video_quality = data.get('video_quality', 'high')  # 'low', 'medium', 'high', 'production'
    
    # ALWAYS use server-side path (ignore client-provided path which may be Windows)
    output_dir = str(VIDEO_OUTPUT_DIR)
    
    # Ensure output directory exists
    VIDEO_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Default watermark patch settings (not exposed to users)
    patch_width = 400
    patch_height = 70
    patch_position = 'bottom-right'
    
    # Validate required fields
    if not problem_statement:
        return jsonify({'success': False, 'error': 'Problem statement is required'}), 400
    
    # Get customer ID for Firebase storage
    customer_id = get_current_customer_id()
    
    # Create job ID and initialize job tracking
    job_id = f"video_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    update_job_status(job_id, {
        'status': 'running',
        'progress': 0,
        'message': 'Starting video generation...',
        'started_at': datetime.now().isoformat(),
        'problem': problem_statement,
        'customer_id': customer_id
    })
    
    logger.info(f"Created video job: {job_id}")
    logger.info(f"Active video jobs: {list(video_jobs.keys())}")
    
    # Start background thread
    thread = Thread(
        target=_generate_video_background,
        args=(job_id, problem_statement, background_color, api_type, 
              video_quality, output_dir, patch_width, patch_height, patch_position)
    )
    thread.daemon = True
    thread.start()
    
    logger.info(f"Started background thread for job: {job_id}")
    logger.info(f"Returning job_id to client: {job_id}")
    
    response = jsonify({
        'success': True,
        'job_id': job_id,
        'message': 'Video generation started in background'
    })
    logger.info(f"Response being sent: {response.get_json()}")
    return response


@app.route('/api/video/status/<job_id>', methods=['GET'])
@login_required
def api_video_status(job_id):
    """API: Check video generation job status."""
    logger.info(f"Status check for job: {job_id}")
    logger.info(f"App start ID: {APP_START_ID}, PID: {os.getpid()}, Uptime: {time.time() - APP_START_TIME:.1f}s")
    logger.info(f"Available jobs: {list(video_jobs.keys())}")
    
    if job_id not in video_jobs:
        # Try loading from filesystem
        job = load_job_status(job_id)
        if job:
            # Restore to memory
            video_jobs[job_id] = job
            logger.info(f"Restored job {job_id} from filesystem")
        else:
            logger.error(f"Job not found: {job_id}")
            return jsonify({
                'success': False, 
                'error': f'Job not found: {job_id}',
                'available_jobs': list(video_jobs.keys())
            }), 404
    
    job = video_jobs[job_id]
    response = {
        'success': True,
        'status': job['status'],
        'progress': job['progress'],
        'message': job['message']
    }
    
    if job['status'] == 'completed':
        response['result'] = job.get('result', {})
    
    logger.info(f"Job {job_id} status: {job['status']}, progress: {job['progress']}%")
    return jsonify(response)


@app.route('/api/video/download/<job_id>', methods=['GET'])
@login_required
def api_download_video(job_id):
    """API: Download a generated video file."""
    from flask import send_file
    
    # Get job status
    job = get_job_status(job_id)
    if not job:
        return jsonify({'success': False, 'error': 'Job not found'}), 404
    
    if job.get('status') != 'completed':
        return jsonify({'success': False, 'error': 'Video not ready yet'}), 400
    
    result = job.get('result', {})
    video_path = result.get('processed_video')
    
    if not video_path or not Path(video_path).exists():
        # Try original URL as fallback
        original_url = result.get('original_url')
        if original_url:
            return redirect(original_url)
        return jsonify({'success': False, 'error': 'Video file not found'}), 404
    
    return send_file(
        video_path,
        mimetype='video/mp4',
        as_attachment=True,
        download_name=f'{job_id}.mp4'
    )


@app.route('/api/video/info/<job_id>', methods=['GET'])
@login_required
def api_video_info(job_id):
    """API: Get video URLs for download/viewing."""
    job = get_job_status(job_id)
    if not job:
        return jsonify({'success': False, 'error': 'Job not found'}), 404
    
    result = job.get('result', {})
    
    return jsonify({
        'success': True,
        'job_id': job_id,
        'status': job.get('status'),
        'original_url': result.get('original_url'),  # Knolify hosted URL
        'vtt_file': result.get('vtt_file'),
        'srt_file': result.get('srt_file'),
        'download_url': f'/api/video/download/{job_id}' if job.get('status') == 'completed' else None
    })


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
