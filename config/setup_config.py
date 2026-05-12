#!/usr/bin/env python3
"""
Configuration Setup Script for TEP LLM System
Helps users set up API keys and configuration files safely.
"""

import json
import os
import shutil
from pathlib import Path

def setup_config():
    """Set up configuration files with user's API keys."""
    
    print("🔧 TEP LLM System Configuration Setup")
    print("=" * 50)
    
    # Get API keys from user
    print("\n📋 Please provide your API keys:")
    print("(Press Enter to skip any provider you don't want to use)")
    
    anthropic_key = input("Anthropic API Key: ").strip()
    google_key = input("Google Gemini API Key: ").strip()
    
    # Load template
    template_path = "config.template.json"
    if not os.path.exists(template_path):
        print(f"❌ Template file {template_path} not found!")
        return False
    
    with open(template_path, 'r') as f:
        config = json.load(f)
    
    # Update with user's keys
    if anthropic_key:
        config["llm_providers"]["anthropic"]["api_key"] = anthropic_key
    if google_key:
        config["llm_providers"]["google"]["api_key"] = google_key
    
    # Create config files
    config_paths = [
        "backend/config.json",
        "frontend/config.json"
    ]
    
    for config_path in config_paths:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        
        # Write config file
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        
        print(f"✅ Created: {config_path}")
    
    print("\n🎉 Configuration setup complete!")
    print("\n⚠️  IMPORTANT:")
    print("- Your API keys are now in config.json files")
    print("- These files are in .gitignore and won't be committed to Git")
    print("- Keep your API keys secure and don't share them")
    
    return True

if __name__ == "__main__":
    setup_config()
