#!/usr/bin/env python3
"""
File Monitor Agent for SWF Fast Monitoring System.

This agent monitors DAQ directories for newly created STF files, selects a fraction
of them based on configuration, and records them in the fast monitoring database.

Designed to run continuously under supervisord.
"""

import os
import sys
import time
import logging
import hashlib
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional
from urllib.parse import urlparse

import django

# Configure Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'swf_fastmon_agent.database.settings')
django.setup()

from swf_fastmon_agent.database.models import Run, StfFile, FileStatus


class FileMonitorAgent:
    """
    Agent that monitors directories for new STF files and records them in the database.
    """
    
    def __init__(self, config: dict):
        """
        Initialize the file monitor agent.
        
        Args:
            config: Configuration dictionary containing:
                - watch_directories: List of directories to monitor
                - file_patterns: List of file patterns to match (e.g., ['*.stf'])
                - check_interval: Seconds between directory scans
                - lookback_time: Minutes to look back for new files
                - selection_fraction: Fraction of files to select (0.0-1.0)
                - default_run_number: Run number to use if not detected from filename
                - base_url: Base URL for constructing file URLs
        """
        self.config = config
        self.logger = self._setup_logging()
        self.running = False
        
        # Validate configuration
        self._validate_config()
        
        self.logger.info(f"File Monitor Agent initialized with config: {config}")
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging configuration."""
        # TODO: Switch to SWF common logging

        logger = logging.getLogger('swf_fastmon_agent.file_monitor')
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def _validate_config(self):
        """Validate the configuration parameters."""
        required_keys = [
            'watch_directories', 'file_patterns', 'check_interval',
            'lookback_time', 'selection_fraction', 'default_run_number'
        ]
        
        for key in required_keys:
            if key not in self.config:
                raise ValueError(f"Missing required configuration key: {key}")
        
        if not (0.0 <= self.config['selection_fraction'] <= 1.0):
            raise ValueError("selection_fraction must be between 0.0 and 1.0")
    
    def _find_recent_files(self) -> List[Path]:
        """
        Find files created within the lookback time period.
        
        Returns:
            List of Path objects for matching files
        """
        cutoff_time = datetime.now() - timedelta(minutes=self.config['lookback_time'])
        cutoff_timestamp = cutoff_time.timestamp()
        
        matching_files = []
        
        for directory in self.config['watch_directories']:
            dir_path = Path(directory)
            if not dir_path.exists():
                self.logger.warning(f"Watch directory does not exist: {directory}")
                continue
            
            try:
                for pattern in self.config['file_patterns']:
                    for file_path in dir_path.glob(pattern):
                        if file_path.is_file():
                            # Check if file was created after cutoff time
                            if file_path.stat().st_ctime > cutoff_timestamp:
                                matching_files.append(file_path)
                                
            except Exception as e:
                self.logger.error(f"Error scanning directory {directory}: {e}")
        
        return matching_files
    
    def _select_files(self, files: List[Path]) -> List[Path]:
        """
        Select a fraction of files based on configuration.
        
        Args:
            files: List of file paths to select from
            
        Returns:
            List of selected file paths
        """
        if not files:
            return []
        
        selection_count = max(1, int(len(files) * self.config['selection_fraction']))
        
        # Use random selection
        selected = random.sample(files, min(selection_count, len(files)))
        
        self.logger.info(f"Selected {len(selected)} files out of {len(files)} candidates")
        return selected
    
    def _extract_run_number(self, file_path: Path) -> int:
        """
        Extract run number from filename or use default.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Run number
        """
        # Try to extract run number from filename
        # Example: assume filename format like "run_12345_stf_001.stf"
        filename = file_path.name
        
        # Look for run number patterns
        import re
        patterns = [
            r'run_(\d+)',
            r'run(\d+)',
            r'r(\d+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, filename, re.IGNORECASE)
            if match:
                return int(match.group(1))
        
        # Use default run number if not found
        return self.config['default_run_number']
    
    def _calculate_checksum(self, file_path: Path) -> str:
        """
        Calculate MD5 checksum of file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            MD5 checksum string
        """
        hash_md5 = hashlib.md5()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception as e:
            self.logger.error(f"Error calculating checksum for {file_path}: {e}")
            return ""
    
    def _get_or_create_run(self, run_number: int) -> Run:
        """
        Get or create a Run object for the given run number.
        
        Args:
            run_number: Run number
            
        Returns:
            Run object
        """
        run, created = Run.objects.get_or_create(
            run_number=run_number,
            defaults={
                'start_time': datetime.now(),
                'run_conditions': {'auto_created': True}
            }
        )
        
        if created:
            self.logger.info(f"Created new run: {run_number}")
        
        return run
    
    def _construct_file_url(self, file_path: Path) -> str:
        """
        Construct URL for file access.
        
        Args:
            file_path: Path to the file
            
        Returns:
            URL string
        """
        base_url = self.config.get('base_url', 'file://')
        if base_url.endswith('/'):
            base_url = base_url[:-1]
        
        # Convert to absolute path and create URL
        abs_path = file_path.resolve()
        return f"{base_url}{abs_path}"
    
    def _record_file(self, file_path: Path):
        """
        Record a file in the database.

        Args:
            file_path: Path to the file to record
        """
        try:
            # Check if file already exists in database
            file_url = self._construct_file_url(file_path)
            if StfFile.objects.filter(file_url=file_url).exists():
                self.logger.debug(f"File already recorded: {file_path}")
                return
            
            # Get file information
            file_stat = file_path.stat()
            file_size = file_stat.st_size
            
            # Extract run number and get/create run
            run_number = self._extract_run_number(file_path)
            run = self._get_or_create_run(run_number)
            
            # Calculate checksum (optional, can be expensive)
            checksum = ""
            if self.config.get('calculate_checksum', False):
                checksum = self._calculate_checksum(file_path)
            
            # Create STF file record
            stf_file = StfFile.objects.create(
                run=run,
                file_url=file_url,
                file_size_bytes=file_size,
                checksum=checksum,
                status=FileStatus.REGISTERED,
                metadata={
                    'original_path': str(file_path),
                    'creation_time': datetime.fromtimestamp(file_stat.st_ctime).isoformat(),
                    'modification_time': datetime.fromtimestamp(file_stat.st_mtime).isoformat(),
                    'agent_version': '1.0.0',
                }
            )
            
            self.logger.info(f"Recorded file: {file_path} -> {stf_file.file_id}")
            
        except Exception as e:
            self.logger.error(f"Error recording file {file_path}: {e}")
    
    def _process_files(self):
        """Process a single scan cycle."""
        try:
            # Find recent files
            recent_files = self._find_recent_files()
            
            if not recent_files:
                self.logger.debug("No recent files found")
                return
            
            # Select fraction of files
            selected_files = self._select_files(recent_files)
            
            # Record selected files
            for file_path in selected_files:
                self._record_file(file_path)
                
        except Exception as e:
            self.logger.error(f"Error in process cycle: {e}")
    
    def start(self):
        """Start the file monitoring agent."""
        self.running = True
        self.logger.info("File Monitor Agent started")
        
        try:
            while self.running:
                self._process_files()
                
                # Sleep for the configured interval
                time.sleep(self.config['check_interval'])
                
        except KeyboardInterrupt:
            self.logger.info("Received interrupt signal")
        except Exception as e:
            self.logger.error(f"Unexpected error in main loop: {e}")
        finally:
            self.running = False
            self.logger.info("File Monitor Agent stopped")
    
    def stop(self):
        """Stop the file monitoring agent."""
        self.running = False


def main():
    """Main entry point for the agent."""
    # Example configuration - in production, this would come from config file
    config = {
        'watch_directories': [
            '/data/DAQbuffer/',
        ],
        'file_patterns': ['*.stf', '*.STF'],
        'check_interval': 30,  # seconds
        'lookback_time': 5,    # minutes
        'selection_fraction': 0.1,  # 10% of files
        'default_run_number': 1,
        'base_url': 'file://',
        'calculate_checksum': False,  # Set to True if checksums are needed
    }
    
    # Override config from environment variables if present
    if 'FASTMON_WATCH_DIRS' in os.environ:
        config['watch_directories'] = os.environ['FASTMON_WATCH_DIRS'].split(',')
    
    if 'FASTMON_FRACTION' in os.environ:
        config['selection_fraction'] = float(os.environ['FASTMON_FRACTION'])
    
    if 'FASTMON_INTERVAL' in os.environ:
        config['check_interval'] = int(os.environ['FASTMON_INTERVAL'])
    
    if 'FASTMON_LOOKBACK' in os.environ:
        config['lookback_time'] = int(os.environ['FASTMON_LOOKBACK'])
    
    # Create and start agent
    agent = FileMonitorAgent(config)
    agent.start()


if __name__ == '__main__':
    main()