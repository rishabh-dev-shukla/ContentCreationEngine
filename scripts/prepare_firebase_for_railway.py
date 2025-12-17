"""
Helper script to convert Firebase service account JSON to single-line format
for use as an environment variable in Railway or other deployment platforms.
"""

import json
import sys
from pathlib import Path

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
DATABASE_DIR = PROJECT_ROOT / "database"

def convert_firebase_json_to_env():
    """Convert Firebase JSON file to single-line format for environment variable."""
    
    # Find Firebase credentials file
    cred_files = list(DATABASE_DIR.glob("*.json"))
    
    if not cred_files:
        print("❌ No Firebase credentials file found in database/ folder")
        sys.exit(1)
    
    cred_file = cred_files[0]
    print(f"📄 Found Firebase credentials: {cred_file.name}\n")
    
    # Read and minify JSON
    with open(cred_file, 'r') as f:
        cred_data = json.load(f)
    
    # Convert to single-line JSON (minified)
    single_line = json.dumps(cred_data, separators=(',', ':'))
    
    # Output
    print("=" * 80)
    print("FIREBASE_SERVICE_ACCOUNT environment variable:")
    print("=" * 80)
    print(single_line)
    print("=" * 80)
    print("\n📋 Copy the above line and add it as FIREBASE_SERVICE_ACCOUNT in Railway")
    print("\nSteps:")
    print("1. Go to your Railway project dashboard")
    print("2. Click on your service → Variables tab")
    print("3. Click 'New Variable'")
    print("4. Name: FIREBASE_SERVICE_ACCOUNT")
    print("5. Value: Paste the JSON line above")
    print("6. Click 'Add'")
    
    # Save to a file for convenience
    output_file = PROJECT_ROOT / "firebase_env_credential.txt"
    with open(output_file, 'w') as f:
        f.write(single_line)
    
    print(f"\n✅ Also saved to: {output_file}")
    print("⚠️  Remember to delete this file after copying to Railway!")

if __name__ == '__main__':
    convert_firebase_json_to_env()
