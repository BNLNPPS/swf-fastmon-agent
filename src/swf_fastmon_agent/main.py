#!/usr/bin/env python3
"""
Fast Monitoring Agent for SWF Fast Monitoring System.

This agent receives stf_ready messages from the data agent, samples Time Frames (TF) from
Super Time Frames (STF), and records TF metadata in the fast monitoring database.
The TFs are then broadcast via ActiveMQ to fast monitoring clients.

Designed to run continuously under supervisord.
"""

import sys
import json
from datetime import datetime

from swf_common_lib.base_agent import BaseAgent, setup_environment
import fastmon_utils as fastmon_utils


class FastMonitorAgent(BaseAgent):
    """
    Agent that receives stf_ready messages, samples TFs from STFs and records them in the database.
    Then broadcasts the TF notifications via ActiveMQ.
    """

    def __init__(self, config: dict, debug=False):
        """
        Initialize the fast monitoring agent.

        Args:
            config: configuration dictionary containing:
                - selection_fraction: Fraction of TFs to select (0.0-1.0)
                - tf_files_per_stf: Number of TF files to generate per STF
                - tf_size_fraction: Fraction of STF size for each TF
                - tf_sequence_start: Starting sequence number for TF files
            debug: Enable debug logging for heartbeat messages
        """

        # Initialize base agent with fast monitoring specific parameters
        super().__init__(agent_type='fastmon', subscription_queue='epictopic', debug=debug)
        self.running = True

        self.logger.info("Fast Monitor Agent initialized successfully")

        self.config = config

        # Validate configuration
        fastmon_utils.validate_config(self.config)
        self.logger.info(f"Fast Monitor Agent initialized with config: {self.config}")

        # Fast monitoring specific state
        self.stf_messages_processed = 0
        self.last_message_time = None
        self.processing_stats = {'total_stf_messages': 0, 'total_tf_files_created': 0}


    def _emulate_stf_registration_and_sampling(self):
        """
        NOTE: This method emulates the STF registration and TF sampling process for development purposes.
        Process STF files in a single scan cycle, samples a fraction of TFs, and broadcasts them to message queues.
        """

        try:
            self.last_scan_time = datetime.now()
            tf_files_registered = []
            self.logger.debug("Starting STF file registration and TF sampling process")
            # Find the most recent STF files based on the time window set in the configuration
            recent_files = fastmon_utils.find_recent_files(self.config, self.logger)
            if not recent_files:
                self.logger.warning("No recent files found")
                return
            self.logger.debug(f"Found {len(recent_files)} STF files to process")
            self.processing_stats['total_files'] += len(recent_files)

            # Sample a fraction of the files based on the selection fraction
            if self.config['selection_fraction'] < 1.0:
                self.logger.debug(f"Sampling {self.config['selection_fraction'] * 100}% of recent files")
                recent_files = fastmon_utils.sample_files(recent_files, self.config['selection_fraction'], self.logger)

            # For TEST, kee only the first 2 files
            if len(recent_files) > 2:
                self.logger.warning(f"TEST MODE: Limiting processing to first 2 files for testing purposes")
                recent_files = recent_files[:2]

            # Register the files in the swf monitoring database as STF files
            for file_path in recent_files:
                self.logger.debug(f"Processing {file_path} for registration and sampling")
                stf_file = fastmon_utils.record_stf_file(file_path, self.config, self, self.logger)
                self.files_processed += 1

                # Simulate TF subsamples for this STF file
                tf_subsamples = fastmon_utils.simulate_tf_subsamples(stf_file, file_path, self.config, self.logger)

                # Record each TF file in the FastMonFile table
                tf_files_created = 0
                for tf_metadata in tf_subsamples:
                    tf_file = fastmon_utils.record_tf_file(stf_file, tf_metadata, self.config, self, self.logger)
                    if tf_file:
                        tf_files_created += 1
                        # Send notification to clients about new TF file
                        self.send_tf_file_notification(tf_file, stf_file)
                    tf_files_registered.append(tf_file)

                self.logger.info(f"Registered {tf_files_created} TF subsamples for STF file {stf_file['filename']}")

            # Report successful processing
            self.report_agent_status('OK', f'Emulating {len(tf_files_registered)} fast monitoring files')
            return tf_files_registered

        except Exception as e:
            self.logger.error(f"Error in process cycle: {e}")
            self.report_agent_status('ERROR', f'Fast monitoring emulation error: {str(e)}')
            return None


    def send_tf_file_notification(self, tf_file: dict, stf_file: dict):
        """
        Send notification to clients about a newly registered TF file via ActiveMQ.

        Args:
            tf_file: TF file data from the FastMonFile API
            stf_file: Parent STF file data
        """
        try:
            # Create message using utility function
            message = fastmon_utils.create_tf_message(tf_file, stf_file, self.agent_name)

            # Send message via ActiveMQ (monitor will forward to SSE clients)
            self.send_message(self.destination, message)

            self.logger.debug(f"Sent TF file notification via ActiveMQ: {tf_file.get('tf_filename')}")

        except Exception as e:
            self.logger.error(f"Failed to send TF file notification: {e}")

    def on_message(self, frame):
        """
        Handle incoming stf_ready messages for fast monitoring.
        This agent processes STF metadata and creates TF samples.
        """
        # Use base class helper for consistent logging
        message_data, msg_type = self.log_received_message(frame, {'stf_ready'})

        # Update heartbeat on message activity
        self.send_heartbeat()

        try:
            # A "stf_ready" call from the data agent
            if msg_type == 'stf_ready':
                tf_files = self.sample_timeframes(message_data)
            else:
                self.logger.warning(f"Ignoring unknown message type {msg_type}", extra={"msg_type": msg_type})

        except Exception as e:
            self.logger.error("Error processing message", extra={"error": str(e)})
            self.report_agent_status('ERROR', f'Message processing error: {str(e)}')

    def sample_timeframes(self, message_data):
        """
        Handle stf_ready message and sample STFs into TFs
        Registers the TFs in the swf-monitor database and notifies clients.
        """
        self.logger.info("Processing stf_ready message")

        # Update message tracking stats
        self.last_message_time = datetime.now()
        self.stf_messages_processed += 1
        self.processing_stats['total_stf_messages'] += 1

        tf_files_registered = []
        self.logger.debug(f"Message data received: {message_data}")
        if not message_data.get('filename'):
            self.logger.error("No filename provided in message")
            return tf_files_registered

        tf_subsamples = fastmon_utils.simulate_tf_subsamples(message_data, self.config, self.logger, self.agent_name)

        # Record each TF file in the FastMonFile table
        # TODO: register in bulk
        tf_files_created = 0
        for tf_metadata in tf_subsamples:
            self.logger.debug(f"Processing {tf_metadata}")
            tf_file = fastmon_utils.record_tf_file(tf_metadata, self.config, self, self.logger)
            if tf_file:
                tf_files_created += 1
            tf_files_registered.append(tf_file)

        # Update TF creation stats
        self.processing_stats['total_tf_files_created'] += tf_files_created

        self.logger.info(f"Registered {tf_files_created} TF subsamples for STF file {message_data.get('filename')}")
        return tf_files_registered

    def start_continuous_monitoring(self):
        """
        Start continuous file monitoring
        NOTE: Intended for development and testing purposes.
        """
        self.logger.info("Starting continuous fast monitoring (DEV MODE)...")
        
        try:
            while True:
                tf_files_created = self._emulate_stf_registration_and_sampling()
                self.send_heartbeat()
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
    import argparse

    parser = argparse.ArgumentParser(description='Fast Monitor Agent')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging for heartbeat messages')
    args = parser.parse_args()

    # Configuration for message-driven agent
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
    }

    # Create agent with config and debug flag
    agent = FastMonitorAgent(config, debug=args.debug)

    # Check if we should run in message-driven mode or continuous mode
    mode = os.getenv('FASTMON_MODE', '').lower()

    if mode:
        # Run in continuous monitoring mode
        agent.start_continuous_monitoring()
    else:
        # Run in message-driven mode (default, integrates with workflow)
        agent.run()


if __name__ == "__main__":
    # Setup environment first
    if not setup_environment():
        sys.exit(1)

    main()
