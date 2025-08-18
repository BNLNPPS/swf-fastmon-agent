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
import json
from datetime import datetime

# Import the centralized logging from swf-common-lib
#from swf_common_lib.rest_logging import setup_rest_logging

from swf_common_lib.base_agent import BaseAgent
from swf_fastmon_agent import fastmon_utils


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
        super().__init__(agent_type='fastmon', subscription_queue='fastmon_agent')
        self.running = True

        self.logger.info("Fast Monitor Agent initialized successfully")

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
            # TF simulation parameters
            "tf_files_per_stf": 7,  # Number of TF files to generate per STF
            "tf_size_fraction": 0.15,  # Fraction of STF size for each TF
            "tf_sequence_start": 1,  # Starting sequence number for TF files
            "agent_name": "swf-fastmon-agent",  # Agent name for tracking
        }
        
        # Validate configuration
        fastmon_utils.validate_config(self.config)
        self.logger.info(f"Fast Monitor Agent initialized with config: {self.config}")
        
        # Fast monitoring specific state
        self.files_processed = 0
        self.last_scan_time = None
        self.processing_stats = {'total_files': 0, 'selected_files': 0}

    def _emulate_stf_registration_and_sampling(self):
        """
        NOTE: This method emulates the STF registration and TF sampling process for development purposes.
        Process STF files in a single scan cycle, samples a fraction of TFs, and broadcasts them to message queues.
        """

        try:
            self.last_scan_time = datetime.now()

            tf_files_registered = []
            
            # Find the most recent STF files based on the time window set in the configuration
            recent_files = fastmon_utils.find_recent_files(self.config, self.logger)
            if not recent_files:
                self.logger.debug("No recent files found")
                return

            self.processing_stats['total_files'] += len(recent_files)

            # Register the files in the swf monitoring database as STF files
            for file_path in recent_files:
                stf_file = fastmon_utils.record_file(file_path, self.config, self, self.logger)
                self.files_processed += 1

                # Simulate TF subsamples for this STF file
                tf_subsamples = fastmon_utils.simulate_tf_subsamples(stf_file, file_path, self.config, self.logger)

                # Record each TF file in the FastMonFile table
                tf_files_created = 0
                for tf_metadata in tf_subsamples:
                    tf_file = fastmon_utils.record_tf_file(stf_file, tf_metadata, self.config, self, self.logger)
                    if tf_file:
                        tf_files_created += 1
                    tf_files_registered.append(tf_file)

                self.logger.info(f"Created {tf_files_created} TF subsamples for STF file {stf_file['stf_filename']}")

            # Report successful processing
            self.report_agent_status('OK', f'Emulating {len(tf_files_registered)} fast monitoring files')
            return tf_files_registered

        except Exception as e:
            self.logger.error(f"Error in process cycle: {e}")
            self.report_agent_status('ERROR', f'Fast monitoring emulation error: {str(e)}')
            return None



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
                self.logger.warning("Ignoring unknown message type", extra={"msg_type": msg_type})

        except Exception as e:
            self.logger.error("Error processing message", extra={"error": str(e)})
            self.report_agent_status('ERROR', f'Message processing error: {str(e)}')
    
    def handle_scan_request(self, message_data):
        """Handle explicit directory scan request."""
        self.logger.info("Processing scan request")
        # TODO: Implement logic to handle data provided (for now it just scans the directory)

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
        """
        Start continuous file monitoring
        NOTE: Intended for development and testing purposes.
        """
        self.logger.info("Starting continuous fast monitoring (DEV MODE)...")
        
        try:
            while True:
                tf_files_created = self._emulate_stf_registration_and_sampling()
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



def main():
    """Main entry point for the agent."""
    # Example configuration - in production, this would come from config file
    # Watch directory is for testing purposes (continuous mode). In production, the agent should react to swf-data-agent messages
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
        # TF simulation parameters
        "tf_files_per_stf": 7,  # Number of TF files to generate per STF
        "tf_size_fraction": 0.15,  # Fraction of STF size for each TF
        "tf_sequence_start": 1,  # Starting sequence number for TF files
        "agent_name": "swf-fastmon-agent",  # Agent name for tracking
    }

    # Create agent with config
    agent = FastMonitorAgent(config)

    # Check if we should run in message-driven mode or continuous mode
    mode = os.getenv('FASTMON_MODE', '').lower()

    if mode:
        # Run in continuous monitoring mode
        agent.start_continuous_monitoring()
    else:
        # Run in message-driven mode (default, integrates with workflow)
        agent.run()


if __name__ == "__main__":
    main()
