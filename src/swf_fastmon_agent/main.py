#!/usr/bin/env python3
"""
File Monitor Agent for SWF Fast Monitoring System.

This agent monitors DAQ directories for newly created STF files, then grabs a fraction of TFs based on configuration,
and records them in the fast monitoring database.
The TFs are then broadcast to message queues for further processing.

Designed to run continuously under supervisord.
"""

import os
import time
import django

# Configure Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "swf_fastmon_agent.database.settings")
django.setup()

from swf_fastmon_agent.agents import fastmon_utils


class FastMonitorAgent:
    """
    Agent that monitors directories for new STF files and records them in the database.
    """

    def __init__(self, config: dict):
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
        self.config = config
        self.logger = fastmon_utils.setup_logging()
        self.running = False

        # Validate configuration
        fastmon_utils.validate_config(self.config)
        self.logger.info(f"File Monitor Agent initialized with config: {config}")

    def _process_files(self):
        """Process STF files in a single scan cycle."""
        try:
            # Find the most recent STF files based on the time window set in the configuration
            recent_files = fastmon_utils.find_recent_files(self.config, self.logger)
            if not recent_files:
                self.logger.debug("No recent files found")
                return

            # Select a fraction of files, emulating TF extraction for now (swf-testbed)
            selected_files = fastmon_utils.select_files(
                recent_files, self.config["selection_fraction"], self.logger
            )

            # Record selected files in the fast monitoring database
            for file_path in selected_files:
                fastmon_utils.record_file(file_path, self.config, self.logger)

            # Broadcast the selected files to message queues
            fastmon_utils.broadcast_files(selected_files, self.config["base_url"], self.logger)


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
                time.sleep(self.config["check_interval"])
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
    # Create and start agent for locating files
    agent = FastMonitorAgent(config)
    agent.start()


if __name__ == "__main__":
    main()
