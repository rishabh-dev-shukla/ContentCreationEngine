"""
Run the ContentCreationEngine Web Application.
Usage: python run_web.py
"""

import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from web.app import create_app

if __name__ == '__main__':
    app = create_app()
    print("\n" + "="*60)
    print("🌐 ContentCreationEngine Web Interface")
    print("="*60)
    print("Starting server at: http://localhost:5000")
    print("Press Ctrl+C to stop the server")
    print("="*60 + "\n")
    
    app.run(
        debug=True,
        host='0.0.0.0',
        port=5000,
        threaded=True
    )
