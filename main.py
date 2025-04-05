#!/usr/bin/env python
"""
Federal Retirement Scenario Explorer

Main launch script for the Federal Retirement Calculator application.
Run this file to start the application.
"""

import os
import sys
import subprocess

def check_dependencies():
    """Check if required packages are installed"""
    try:
        import streamlit
        import pandas
        import numpy
        import matplotlib
        return True
    except ImportError as e:
        print(f"Missing dependency: {e}")
        return False

def install_dependencies():
    """Install required packages"""
    print("Installing dependencies...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        return True
    except subprocess.CalledProcessError:
        print("Failed to install dependencies. Please run:")
        print("pip install -r requirements.txt")
        return False

def main():
    """Main entry point"""
    # Check if streamlit_app.py exists
    if not os.path.exists("streamlit_app.py"):
        print("Error: streamlit_app.py not found!")
        return 1
    
    # Check dependencies
    if not check_dependencies():
        if not install_dependencies():
            return 1
    
    # Run streamlit
    print("Starting Federal Retirement Scenario Explorer...")
    subprocess.call(["streamlit", "run", "streamlit_app.py"])
    
    return 0

if __name__ == "__main__":
    sys.exit(main())