#!/usr/bin/env python3
"""
File Monitor Agent for SWF Fast Monitoring System.

This agent monitors DAQ directories for newly created STF files, then grabs a fraction of TFs based on configuration,
and records metadata in the fast monitoring table.
The TFs are then broadcast to message queues to the fast monitoring clients.

Designed to run continuously under supervisord.
"""

import os
import sys
import time
import django
import json
from pathlib import Path
from datetime import datetime

# Add the swf-testbed example_agents directory to Python path to import base_agent
script_dir = Path(__file__).resolve().parent.parent.parent.parent
swf_testbed_path = script_dir / "swf-testbed" / "example_agents"
if swf_testbed_path.exists():
    sys.path.insert(0, str(swf_testbed_path))
else:
    print(f"Warning: swf-testbed example_agents path not found at {swf_testbed_path}")

from swf_common_lib.base_agent import BaseAgent

# Configure Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "swf_monitor_project.settings")
django.setup()

from swf_fastmon_agent import fastmon_utils


def main():
    """Main entry point for the agent."""
    # Example configuration - in production, this would come from config file
    config = {
        "watch_directories": [
            "/Users/villanueva/tmp/DAQbuffer",
        ],
        "file_patterns": ["*.stf", "*.STF"],
        "check_interval": 30,  # seconds
        "lookback_time": 0,  # minutes
        "selection_fraction": 0.1,  # 10% of files
        "default_run_number": 1,
        "base_url": "file://",
        "calculate_checksum": True,
    }

    # Create agent with config
    agent = FastMonitorAgent(config)

    # Check if we should run in message-driven mode or continuous mode
    mode = os.getenv('FASTMON_MODE', '').lower()

    if mode == 'continuous':
        # Run in continuous monitoring mode
        agent.start_continuous_monitoring()
    else:
        # Run in message-driven mode (default, integrates with workflow)
        agent.run()


class FastMonitorAgent(BaseAgent):
    """
    Agent that monitors directories for new STF files, samples TFs and records them in the database. Then broadcasts
    the selected files to message queues.
    """

    def __init__(self, config: dict = None):
        """
        Initialize the file monitor agent.

        Args:
            config: configuration dictionary containing:
                - watch_directories: List of directories to monitor
                - file_patterns: List of file patterns to match (e.g., ['*.stf'])
                - check_interval: Seconds between directory scans
                - lookback_time: Minutes to look back for new files
                - selection_fraction: Fraction of files to select (0.0-1.0)
                - default_run_number: Run number to use if not detected from filename
                - base_url: Base URL for constructing file URLs
        """
        # Initialize base agent with fast monitoring specific parameters
        super().__init__(agent_type='FASTMON', subscription_queue='fastmon_agent')
        
        # Set default config if none provided
        self.config = config or {
            "watch_directories": [
                "/Users/villanueva/tmp/DAQbuffer",
            ],
            "file_patterns": ["*.stf", "*.STF"],
            "check_interval": 30,  # seconds
            "lookback_time": 0,  # minutes
            "selection_fraction": 0.1,  # 10% of files
            "default_run_number": 1,
            "base_url": "file://",
            "calculate_checksum": True,
        }
        
        # Validate configuration
        fastmon_utils.validate_config(self.config)
        self.logger.info(f"Fast Monitor Agent initialized with config: {self.config}")
        
        # Fast monitoring specific state
        self.files_processed = 0
        self.last_scan_time = None
        self.processing_stats = {'total_files': 0, 'selected_files': 0}

    def _process_files(self):
        """Process STF files in a single scan cycle."""
        try:
            self.last_scan_time = datetime.now()
            
            # Find the most recent STF files based on the time window set in the configuration
            recent_files = fastmon_utils.find_recent_files(self.config, self.logger)
            if not recent_files:
                self.logger.debug("No recent files found")
                return

            self.processing_stats['total_files'] += len(recent_files)

            # Select a fraction of files, emulating TF extraction for now (swf-testbed)
            # FIXME: This should be replaced with actual TF extraction logic
            selected_files = fastmon_utils.select_files(
                recent_files, self.config["selection_fraction"], self.logger
            )

            self.processing_stats['selected_files'] += len(selected_files)

            # Record selected files in the fast monitoring database
            for file_path in selected_files:
                fastmon_utils.record_file(file_path, self.config, self.logger)
                self.files_processed += 1

            # Broadcast the selected files to message queues
            if selected_files:
                fastmon_utils.broadcast_files(selected_files, self.config, self.logger)
                
                # Report successful processing
                self.report_agent_status('OK', f'Processed {len(selected_files)} files')

        except Exception as e:
            self.logger.error(f"Error in process cycle: {e}")
            self.report_agent_status('ERROR', f'File processing error: {str(e)}')


    def on_message(self, frame):
        """
        Handle incoming messages for fast monitoring.
        This agent can respond to directory scan requests or run lifecycle events.
        """
        self.logger.info("Fast Monitor Agent received message")
        # Update heartbeat on message activity
        self.send_fastmon_agent_heartbeat()
        
        try:
            message_data = json.loads(frame.body)
            msg_type = message_data.get('msg_type')

            # A "data_ready" call from the swf-data-agent
            if msg_type == 'data_ready':
                self.handle_scan_request(message_data)
            else:
                self.logger.info("Ignoring unknown message type", extra={"msg_type": msg_type})
                # Even for unknown messages, perform a directory scan
                self._process_files()
                
        except Exception as e:
            self.logger.error("Error processing message", extra={"error": str(e)})
            self.report_agent_status('ERROR', f'Message processing error: {str(e)}')
    
    def handle_scan_request(self, message_data):
        """Handle explicit directory scan request."""
        self.logger.info("Processing scan request")
        # TODO: Implement logic to handle data provided (for now it just scans the directory)
        self._process_files()
        self.send_fastmon_agent_heartbeat()

    
    def send_fastmon_agent_heartbeat(self):
        """Send enhanced heartbeat with fast monitoring context."""
        workflow_metadata = {
            'files_processed': self.files_processed,
            'last_scan': self.last_scan_time.isoformat() if self.last_scan_time else None,
            'total_files_seen': self.processing_stats['total_files'],
            'selected_files': self.processing_stats['selected_files']
        }
        
        return self.send_enhanced_heartbeat(workflow_metadata)
    
    def start_continuous_monitoring(self):
        """ Start continuous file monitoring """
        self.logger.info("Starting continuous fast monitoring...")
        
        try:
            while True:
                self._process_files()
                self.send_fastmon_agent_heartbeat()
                # Sleep for the configured interval
                time.sleep(self.config["check_interval"])
        except KeyboardInterrupt:
            self.logger.info("Received interrupt signal")
        except Exception as e:
            self.logger.error(f"Unexpected error in monitoring loop: {e}")
            self.report_agent_status('ERROR', f'Monitoring loop error: {str(e)}')
        finally:
            self.logger.info("Fast Monitor Agent stopped")



if __name__ == "__main__":
    main()
