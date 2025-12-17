"""
Run the ContentCreationEngine Web Application.
Usage: python run_web.py
"""

import sys
import os
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from web.app import create_app

# Create the app instance for gunicorn
app = create_app()

if __name__ == '__main__':
    print("\n" + "="*60)
    print("🌐 ContentCreationEngine Web Interface")
    print("="*60)
    print("Starting server at: http://localhost:5000")
    print("Press Ctrl+C to stop the server")
    print("="*60 + "\n")
    
    port = int(os.environ.get('PORT', 5000))
    app.run(
        debug=os.environ.get('FLASK_ENV') != 'production',
        host='0.0.0.0',
        port=port,
        threaded=True
    )
