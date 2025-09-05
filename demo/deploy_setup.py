#!/usr/bin/env python3
"""
Deployment setup script for Lineagentic-DPC: Data Product Composer
This script handles the deployment configuration and setup.
"""

import os
import sys
from pathlib import Path

def setup_deployment():
    """Setup the deployment environment"""
    print("🔧 Setting up Lineagentic-DPC deployment...")
    
    # Check for required environment variables
    required_vars = ["OPENAI_API_KEY"]
    missing_vars = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        print("Please set these environment variables before deployment.")
        return False
    
    print("✅ Environment variables configured")
    
    # Create necessary directories
    directories = ["sessions", "logs"]
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
        print(f"📁 Created directory: {directory}")
    
    print("✅ Deployment setup completed successfully!")
    return True

if __name__ == "__main__":
    success = setup_deployment()
    if not success:
        sys.exit(1)
