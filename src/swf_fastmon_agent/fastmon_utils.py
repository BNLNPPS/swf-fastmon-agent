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
from typing import List, Dict, Any

# File status constants (matching Django FileStatus choices)
class FileStatus:
    REGISTERED = 'REGISTERED'
    PROCESSING = 'PROCESSING'
    PROCESSED = 'PROCESSED'
    ERROR = 'ERROR'
    ARCHIVED = 'ARCHIVED'


def setup_logging(logger_name: str = "swf_fastmon_agent.file_monitor") -> logging.Logger:
    """Setup logging configuration."""
    # TODO: Switch to SWF common logging

    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger


def validate_config(config: dict) -> None:
    """Validate the configuration parameters."""
    required_keys = [
        "watch_directories",
        "file_patterns",
        "check_interval",
        "lookback_time",
        "selection_fraction",
        "default_run_number",
    ]

    for key in required_keys:
        if key not in config:
            raise ValueError(f"Missing required configuration key: {key}")

    if not (0.0 <= config["selection_fraction"] <= 1.0):
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
    if config["lookback_time"]:
        cutoff_time = datetime.now() - timedelta(minutes=config["lookback_time"])
        cutoff_timestamp = cutoff_time.timestamp()

    matching_files = []

    for directory in config["watch_directories"]:
        dir_path = Path(directory)
        if not dir_path.exists():
            logger.warning(f"Watch directory does not exist: {directory}")
            continue

        try:
            for pattern in config["file_patterns"]:
                for file_path in dir_path.glob(pattern):
                    if file_path.is_file():
                        # Check if file was created after cutoff time, otherwise skip
                        if (
                            cutoff_timestamp
                            and file_path.stat().st_ctime < cutoff_timestamp
                        ):
                            continue
                        matching_files.append(file_path)

        except Exception as e:
            logger.error(f"Error scanning directory {directory}: {e}")

    return matching_files


def select_files(
    files: List[Path], selection_fraction: float, logger: logging.Logger
) -> List[Path]:
    """
    Select a fraction of files based on configuration.

    Args:
        files: List of file paths to select from
        selection_fraction: Fraction of files to select [0.0, 1.0]
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
        r"run_(\d+)",
        r"run(\d+)",
        r"r(\d+)",
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


def get_or_create_run(run_number: int, agent, logger: logging.Logger) -> Dict[str, Any]:
    """
    Get or create a Run object for the given run number using REST API.

    Args:
        run_number: Run number
        agent: BaseAgent instance for API access
        logger: Logger instance

    Returns:
        Run data dictionary
    """
    try:
        # First try to get existing run
        runs_response = agent.call_monitor_api('get', f'/runs/?run_number={run_number}')
        if runs_response.get('results') and len(runs_response['results']) > 0:
            logger.debug(f"Found existing run: {run_number}")
            return runs_response['results'][0]
        
        # Create new run if not found
        run_data = {
            "run_number": run_number,
            "start_time": datetime.now().isoformat(),
            "run_conditions": {"auto_created": True},
        }
        
        new_run = agent.call_monitor_api('post', '/runs/', run_data)
        logger.info(f"Created new run: {run_number}")
        return new_run
        
    except Exception as e:
        logger.error(f"Error getting or creating run {run_number}: {e}")
        raise


def construct_file_url(file_path: Path, base_url: str = "file://") -> str:
    """
    Construct URL for file access (for now it uses a file URL scheme).

    Args:
        file_path: Path to the file
        base_url: Base URL for constructing file URLs

    Returns:
        URL string
    """
    base_url = base_url.rstrip('/')

    # Convert to absolute path and create URL
    abs_path = file_path.resolve()
    return f"{base_url}/{abs_path}"


def record_file(file_path: Path, config: dict, agent, logger: logging.Logger) -> Dict[str, Any]:
    """
    Record a file in the database using REST API.

    Args:
        file_path: Path to the file to record
        config: Configuration dictionary
        agent: BaseAgent instance for API access
        logger: Logger instance
    
    Returns:
        STF file data dictionary
    """
    try:
        # Check if file already exists in database
        file_url = construct_file_url(file_path, config.get("base_url", "file://"))
        
        # Check if file already recorded
        existing_files = agent.call_monitor_api('get', f'/stf-files/?file_url={file_url}')
        if existing_files.get('results') and len(existing_files['results']) > 0:
            logger.debug(f"File already recorded: {file_path}")
            return existing_files['results'][0]

        # Get file information
        file_stat = file_path.stat()
        file_size = file_stat.st_size

        # Extract run number and get/create run
        run_number = extract_run_number(file_path, config["default_run_number"])
        run_data = get_or_create_run(run_number, agent, logger)

        # Calculate checksum (optional, can be expensive)
        checksum = ""
        if config.get("calculate_checksum", False):
            checksum = calculate_checksum(file_path, logger)

        # Create STF file record via API
        stf_file_data = {
            "run": run_data["run_id"],
            "stf_filename": file_path.name,
            "file_url": file_url,
            "file_size_bytes": file_size,
            "checksum": checksum,
            "status": FileStatus.REGISTERED,
            "metadata": {
                "original_path": str(file_path),
                "creation_time": datetime.fromtimestamp(file_stat.st_ctime).isoformat(),
                "modification_time": datetime.fromtimestamp(
                    file_stat.st_mtime
                ).isoformat(),
                "agent_version": "1.0.0",
            },
        }

        stf_file = agent.call_monitor_api('post', '/stf-files/', stf_file_data)
        logger.info(f"Recorded file: {file_path} -> {stf_file['file_id']}")
        return stf_file

    except Exception as e:
        logger.error(f"Error recording file {file_path}: {e}")
        raise


def simulate_tf_subsamples(stf_file: Dict[str, Any], file_path: Path, config: dict, logger: logging.Logger) -> List[Dict[str, Any]]:
    """
    Simulate creation of Time Frame (TF) subsamples from a Super Time Frame (STF) file.
    
    Args:
        stf_file: STF file data dictionary from REST API
        file_path: Path to the original STF file
        config: Configuration dictionary
        logger: Logger instance
        
    Returns:
        List of TF metadata dictionaries
    """
    try:
        tf_files_per_stf = config.get("tf_files_per_stf", 7)
        tf_size_fraction = config.get("tf_size_fraction", 0.15)
        tf_sequence_start = config.get("tf_sequence_start", 1)
        
        tf_subsamples = []
        stf_size = stf_file.get("file_size_bytes", 0)
        base_filename = file_path.stem  # filename without extension
        
        for i in range(tf_files_per_stf):
            sequence_number = tf_sequence_start + i
            
            # Generate TF filename based on STF filename
            tf_filename = f"{base_filename}_tf_{sequence_number:03d}.tf"
            
            # Calculate TF file size as fraction of STF size with some randomness
            tf_size = int(stf_size * tf_size_fraction * random.uniform(0.8, 1.2))
            
            # Create TF metadata
            tf_metadata = {
                "tf_filename": tf_filename,
                "file_size_bytes": tf_size,
                "sequence_number": sequence_number,
                "stf_parent": stf_file["file_id"],
                "metadata": {
                    "simulation": True,
                    "created_from": str(file_path),
                    "sequence_number": sequence_number,
                    "tf_size_fraction": tf_size_fraction,
                    "agent_name": config.get("agent_name", "swf-fastmon-agent"),
                }
            }
            
            tf_subsamples.append(tf_metadata)
        
        logger.info(f"Generated {len(tf_subsamples)} TF subsamples for STF {stf_file['stf_filename']}")
        return tf_subsamples
        
    except Exception as e:
        logger.error(f"Error simulating TF subsamples for {file_path}: {e}")
        return []


def record_tf_file(stf_file: Dict[str, Any], tf_metadata: Dict[str, Any], config: dict, agent, logger: logging.Logger) -> Dict[str, Any]:
    """
    Record a Time Frame (TF) file in the database using REST API.
    
    Args:
        stf_file: Parent STF file data dictionary
        tf_metadata: TF metadata dictionary from simulate_tf_subsamples
        config: Configuration dictionary
        agent: BaseAgent instance for API access
        logger: Logger instance
        
    Returns:
        FastMonFile data dictionary or None if failed
    """
    try:
        # Prepare FastMonFile data for API
        tf_file_data = {
            "stf_file": stf_file["file_id"],
            "tf_filename": tf_metadata["tf_filename"],
            "file_size_bytes": tf_metadata["file_size_bytes"],
            "status": FileStatus.REGISTERED,
            "metadata": tf_metadata.get("metadata", {})
        }
        
        # Create TF file record via FastMonFile API
        tf_file = agent.call_monitor_api('post', '/fastmon-files/', tf_file_data)
        logger.debug(f"Recorded TF file: {tf_metadata['tf_filename']} -> {tf_file['tf_file_id']}")
        return tf_file
        
    except Exception as e:
        logger.error(f"Error recording TF file {tf_metadata['tf_filename']}: {e}")
        return None


def broadcast_files(selected_files: list, config: dict, logger: logging.Logger) -> None:
    """
    Broadcast a message to the Active MQ.

    Args:
        selected_files: List with metadata of selected file paths to broadcast
        config: Configuration dictionary
        logger: Logger instance
    """

    # Placeholder for actual broadcast logic

    # message_queue.send(message)