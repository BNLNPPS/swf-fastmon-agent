#!/usr/bin/env python3
"""
Database setup script for the SWF Fast Monitoring Agent
This script initializes the database schema using Django migrations.
"""

import os
import sys
import logging
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Set Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'swf_fastmon_agent.database.settings')

import django
from django.core.management import call_command, execute_from_command_line
from django.conf import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    """Initialize the database schema using Django"""
    try:
        # Setup Django
        django.setup()
        
        # Create migrations
        logger.info("Creating database migrations...")
        call_command('makemigrations', 'database', verbosity=1)
        
        # Apply migrations
        logger.info("Applying database migrations...")
        call_command('migrate', verbosity=1)
        
        # Test by importing and using the database manager
        from swf_fastmon_agent import DatabaseManager
        db_manager = DatabaseManager()
        logger.info("Database setup completed successfully!")
        
    except Exception as e:
        logger.error(f"Database setup failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()