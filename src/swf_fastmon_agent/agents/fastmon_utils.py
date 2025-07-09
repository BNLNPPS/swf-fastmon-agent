#!/usr/bin/env python3
"""
Utility functions for the Fast Monitor Agent.

"""

import logging
import hashlib
import random
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import List

# Django models
from swf_fastmon_agent.database.models import Run, StfFile, FileStatus


def setup_logging(logger_name: str = 'swf_fastmon_agent.file_monitor') -> logging.Logger:
    """Setup logging configuration."""
    # TODO: Switch to SWF common logging

    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.INFO)
    
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    
    return logger


def validate_config(config: dict) -> None:
    """Validate the configuration parameters."""
    required_keys = [
        'watch_directories', 'file_patterns', 'check_interval',
        'lookback_time', 'selection_fraction', 'default_run_number'
    ]
    
    for key in required_keys:
        if key not in config:
            raise ValueError(f"Missing required configuration key: {key}")
    
    if not (0.0 <= config['selection_fraction'] <= 1.0):
        raise ValueError("selection_fraction must be between 0.0 and 1.0")


def find_recent_files(config: dict, logger: logging.Logger) -> List[Path]:
    """
    Find files created within the lookback time period.
    
    Args:
        config: Configuration dictionary
        logger: Logger instance
        
    Returns:
        List of Path objects for matching files
    """
    cutoff_timestamp = None
    if config['lookback_time']:
        cutoff_time = datetime.now() - timedelta(minutes=config['lookback_time'])
        cutoff_timestamp = cutoff_time.timestamp()
    
    matching_files = []
    
    for directory in config['watch_directories']:
        dir_path = Path(directory)
        if not dir_path.exists():
            logger.warning(f"Watch directory does not exist: {directory}")
            continue
        
        try:
            for pattern in config['file_patterns']:
                for file_path in dir_path.glob(pattern):
                    if file_path.is_file():
                        # Check if file was created after cutoff time, otherwise skip
                        if cutoff_timestamp and file_path.stat().st_ctime < cutoff_timestamp:
                            continue
                        matching_files.append(file_path)
                            
        except Exception as e:
            logger.error(f"Error scanning directory {directory}: {e}")
    
    return matching_files


def select_files(files: List[Path], selection_fraction: float, logger: logging.Logger) -> List[Path]:
    """
    Select a fraction of files based on configuration.
    
    Args:
        files: List of file paths to select from
        selection_fraction: Fraction of files to select (0.0-1.0)
        logger: Logger instance
        
    Returns:
        List of selected file paths
    """
    if not files:
        return []
    
    selection_count = max(1, int(len(files) * selection_fraction))
    
    # Use random selection
    selected = random.sample(files, min(selection_count, len(files)))
    
    logger.info(f"Selected {len(selected)} files out of {len(files)} candidates")
    return selected


def extract_run_number(file_path: Path, default_run_number: int) -> int:
    """
    Extract run number from filename or use default.
    
    Args:
        file_path: Path to the file
        default_run_number: Default run number to use if not found
        
    Returns:
        Run number
    """
    # Try to extract run number from filename
    # Example: assume filename format like "run_12345_stf_001.stf"
    filename = file_path.name
    
    # Look for run number patterns
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
    return default_run_number


def calculate_checksum(file_path: Path, logger: logging.Logger) -> str:
    """
    Calculate MD5 checksum of file.
    
    Args:
        file_path: Path to the file
        logger: Logger instance
        
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
        logger.error(f"Error calculating checksum for {file_path}: {e}")
        return ""


def get_or_create_run(run_number: int, logger: logging.Logger) -> Run:
    """
    Get or create a Run object for the given run number.
    
    Args:
        run_number: Run number
        logger: Logger instance
        
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
        logger.info(f"Created new run: {run_number}")
    
    return run


def construct_file_url(file_path: Path, base_url: str = 'file://') -> str:
    """
    Construct URL for file access.
    
    Args:
        file_path: Path to the file
        base_url: Base URL for constructing file URLs
        
    Returns:
        URL string
    """
    if base_url.endswith('/'):
        base_url = base_url[:-1]
    
    # Convert to absolute path and create URL
    abs_path = file_path.resolve()
    return f"{base_url}{abs_path}"


def record_file(file_path: Path, config: dict, logger: logging.Logger) -> None:
    """
    Record a file in the database.

    Args:
        file_path: Path to the file to record
        config: Configuration dictionary
        logger: Logger instance
    """
    try:
        # Check if file already exists in database
        file_url = construct_file_url(file_path, config.get('base_url', 'file://'))
        if StfFile.objects.filter(file_url=file_url).exists():
            logger.debug(f"File already recorded: {file_path}")
            return
        
        # Get file information
        file_stat = file_path.stat()
        file_size = file_stat.st_size
        
        # Extract run number and get/create run
        run_number = extract_run_number(file_path, config['default_run_number'])
        run = get_or_create_run(run_number, logger)
        
        # Calculate checksum (optional, can be expensive)
        checksum = ""
        if config.get('calculate_checksum', False):
            checksum = calculate_checksum(file_path, logger)
        
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
        
        logger.info(f"Recorded file: {file_path} -> {stf_file.file_id}")
        
    except Exception as e:
        logger.error(f"Error recording file {file_path}: {e}")