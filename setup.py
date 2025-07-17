#!/usr/bin/env python3
"""
Setup script for Forex Trading Bot
This script helps with initial setup and configuration
"""

import os
import json
import sys
import getpass
from pathlib import Path


def create_directories():
    """Create necessary directories"""
    dirs = ['logs', 'backtest', 'backtest/results']
    for dir_name in dirs:
        Path(dir_name).mkdir(exist_ok=True)
    print("✓ Created project directories")


def setup_config():
    """Interactive configuration setup"""
    print("\n=== Forex Trading Bot Configuration ===\n")
    
    # Check if config already exists
    if os.path.exists('config.json'):
        response = input("config.json already exists. Overwrite? (y/N): ")
        if response.lower() != 'y':
            print("Keeping existing configuration.")
            return
    
    # Load template
    with open('config_template.json', 'r') as f:
        config = json.load(f)
    
    # Get user inputs
    print("\nOANDA API Configuration:")
    print("(Get these from https://www.oanda.com/account/api)")
    
    config['account_id'] = input("Enter your OANDA Account ID: ").strip()
    config['access_token'] = getpass.getpass("Enter your OANDA API Token: ").strip()
    
    # Practice account
    practice = input("\nUse practice (demo) account? (Y/n): ").strip().lower()
    config['practice'] = practice != 'n'
    
    # Trading parameters
    print("\nTrading Parameters (press Enter for defaults):")
    
    position_size = input(f"Position size [{config['trading']['position_size']}]: ").strip()
    if position_size:
        config['trading']['position_size'] = int(position_size)
    
    max_positions = input(f"Max concurrent positions [{config['trading']['max_positions']}]: ").strip()
    if max_positions:
        config['trading']['max_positions'] = int(max_positions)
    
    # Currency pairs
    print(f"\nCurrent instruments: {', '.join(config['trading']['instruments'])}")
    modify_pairs = input("Modify currency pairs? (y/N): ").strip().lower()
    if modify_pairs == 'y':
        pairs = input("Enter currency pairs (comma-separated, e.g., EUR_USD,GBP_USD): ").strip()
        config['trading']['instruments'] = [p.strip() for p in pairs.split(',')]
    
    # Save configuration
    with open('config.json', 'w') as f:
        json.dump(config, f, indent=4)
    
    print("\n✓ Configuration saved to config.json")
    print("✓ Remember to keep your API credentials secure!")


def install_dependencies():
    """Install Python dependencies"""
    print("\nInstalling dependencies...")
    os.system(f"{sys.executable} -m pip install -r requirements.txt")
    print("✓ Dependencies installed")


def main():
    print("=== Forex Trading Bot Setup ===\n")
    
    # Create directories
    create_directories()
    
    # Install dependencies
    response = input("\nInstall Python dependencies? (Y/n): ").strip().lower()
    if response != 'n':
        install_dependencies()
    
    # Setup configuration
    response = input("\nSetup configuration? (Y/n): ").strip().lower()
    if response != 'n':
        setup_config()
    
    print("\n=== Setup Complete! ===")
    print("\nTo run the bot:")
    print("  Windows: run_bot.bat")
    print("  Linux/Mac: python3 forex_bot.py")
    print("\nFor help, see README.md")


if __name__ == "__main__":
    main()
