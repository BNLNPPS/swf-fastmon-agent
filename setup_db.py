#!/usr/bin/env python3
"""
Database setup script for the SWF Fast Monitoring Agent
This script initializes the database schema and can be used for development setup.
"""

import os
import sys
import logging
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from swf_fastmon_agent import DatabaseManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    """Initialize the database schema"""
    try:
        # Create database manager
        db_manager = DatabaseManager()
        
        # Create all tables
        logger.info("Creating database tables...")
        db_manager.create_tables()
        logger.info("Database tables created successfully!")
        
        # Test connection
        with db_manager.get_session() as session:
            logger.info("Database connection test successful!")
            
    except Exception as e:
        logger.error(f"Database setup failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()