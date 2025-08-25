#!/usr/bin/env python3
"""
Fast Monitoring Client for SWF Testbed

This client receives TF file notifications from the swf-fastmon-agent
and displays them in real-time in the terminal.
"""

import os
import sys
import json
import time
import signal
from datetime import datetime
from typing import Optional, Dict, Any
from pathlib import Path

import typer
from swf_common_lib.base_agent import BaseAgent


class FastMonitoringClient(BaseAgent):
    """
    Client that receives TF file notifications and displays monitoring information.
    """

    def __init__(self):
        """Initialize the fast monitoring client."""
        # Initialize base agent with client-specific parameters
        super().__init__(agent_type='fastmon-client', subscription_queue='/topic/fastmon_client')
        
        # Client-specific state
        self.tf_files_received = 0
        self.total_file_size = 0
        self.run_statistics = {}
        self.start_time = datetime.now()
        self.running = True
        
        # Register signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        self.logger.info("Fast Monitoring Client initialized")

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        self.logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.running = False

    def on_message(self, frame):
        """
        Handle incoming TF file notifications from the FastMon agent.
        """
        try:
            message_data = json.loads(frame.body)
            msg_type = message_data.get('msg_type')

            if msg_type == 'tf_file_registered':
                self._handle_tf_file_notification(message_data)
            else:
                self.logger.warning(f"Unknown message type: {msg_type}")

        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse message JSON: {e}")
        except Exception as e:
            self.logger.error(f"Error processing message: {e}")

    def _handle_tf_file_notification(self, message_data: Dict[str, Any]):
        """
        Process and display TF file notification.
        
        Args:
            message_data: TF file notification data
        """
        try:
            # Extract notification data
            tf_file_id = message_data.get('tf_file_id')
            tf_filename = message_data.get('tf_filename')
            file_size = message_data.get('file_size_bytes', 0)
            stf_filename = message_data.get('stf_filename')
            run_number = message_data.get('run_number')
            status = message_data.get('status')
            timestamp = message_data.get('timestamp')
            agent_name = message_data.get('agent_name')

            # Update statistics
            self.tf_files_received += 1
            self.total_file_size += file_size
            
            # Update run statistics
            if run_number:
                if run_number not in self.run_statistics:
                    self.run_statistics[run_number] = {
                        'tf_count': 0, 
                        'total_size': 0, 
                        'first_seen': timestamp
                    }
                self.run_statistics[run_number]['tf_count'] += 1
                self.run_statistics[run_number]['total_size'] += file_size

            # Display notification
            self._display_tf_notification(
                tf_filename, file_size, stf_filename, run_number, status, timestamp
            )

            self.logger.debug(f"Processed TF file notification: {tf_filename}")

        except Exception as e:
            self.logger.error(f"Error handling TF file notification: {e}")

    def _display_tf_notification(self, tf_filename: str, file_size: int, 
                                stf_filename: str, run_number: int, 
                                status: str, timestamp: str):
        """
        Display TF file notification in formatted terminal output.
        """
        try:
            # Parse timestamp
            ts = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            time_str = ts.strftime('%H:%M:%S')
            
            # Format file size
            if file_size > 1024 * 1024:
                size_str = f"{file_size / (1024*1024):.1f}MB"
            elif file_size > 1024:
                size_str = f"{file_size / 1024:.1f}KB"
            else:
                size_str = f"{file_size}B"

            # Color coding for status
            status_color = {
                'registered': '\033[92m',  # Green
                'processing': '\033[93m',  # Yellow
                'processed': '\033[94m',   # Blue
                'failed': '\033[91m',      # Red
                'done': '\033[95m'         # Magenta
            }.get(status.lower(), '\033[0m')  # Default no color
            
            reset_color = '\033[0m'

            # Print formatted notification
            print(f"[{time_str}] TF: {tf_filename:<25} | "
                  f"Size: {size_str:>8} | "
                  f"STF: {stf_filename:<20} | "
                  f"Run: {run_number:>4} | "
                  f"Status: {status_color}{status:<10}{reset_color}")

        except Exception as e:
            # Fallback to simple display if formatting fails
            print(f"[{timestamp}] TF: {tf_filename} | Size: {file_size} | STF: {stf_filename} | Run: {run_number} | Status: {status}")

    def display_summary(self):
        """Display summary statistics."""
        uptime = datetime.now() - self.start_time
        uptime_str = str(uptime).split('.')[0]  # Remove microseconds
        
        print("\n" + "="*80)
        print("FAST MONITORING CLIENT SUMMARY")
        print("="*80)
        print(f"Uptime: {uptime_str}")
        print(f"TF Files Received: {self.tf_files_received}")
        print(f"Total Data Size: {self.total_file_size / (1024*1024):.2f} MB")
        
        if self.run_statistics:
            print(f"Active Runs: {len(self.run_statistics)}")
            print("\nRun Statistics:")
            print("-" * 50)
            for run_num, stats in sorted(self.run_statistics.items()):
                print(f"  Run {run_num:>4}: {stats['tf_count']:>3} TF files, "
                      f"{stats['total_size'] / (1024*1024):.2f} MB")
        
        print("="*80)

    def start_monitoring(self):
        """
        Start the monitoring client with enhanced output.
        """
        print("\n" + "="*80)
        print("FAST MONITORING CLIENT STARTED")
        print("="*80)
        print(f"Connected to: {self.mq_host}:{self.mq_port}")
        print(f"Subscription: {self.subscription_queue}")
        print(f"Started at: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print("Press Ctrl+C to stop")
        print("="*80)
        print("TF File Notifications:")
        print("-" * 80)

        try:
            # Override the base run method to add custom monitoring logic
            self.logger.info(f"Starting {self.agent_name}...")
            self.logger.info(f"Connecting to ActiveMQ at {self.mq_host}:{self.mq_port}")
            
            # Track MQ connection status
            self.mq_connected = False
            
            self.conn.connect(
                self.mq_user, 
                self.mq_password, 
                wait=True, 
                version='1.1',
                headers={
                    'client-id': self.agent_name,
                    'heart-beat': '10000,30000'
                }
            )
            self.mq_connected = True
            self.logger.info("Successfully connected to ActiveMQ")
            
            self.conn.subscribe(destination=self.subscription_queue, id=1, ack='auto')
            self.logger.info(f"Subscribed to queue: '{self.subscription_queue}'")

            # Monitor loop
            while self.running:
                time.sleep(1)
                
                # Check connection status
                if not self.mq_connected:
                    self._attempt_reconnect()

        except KeyboardInterrupt:
            self.logger.info("Received interrupt signal")
        except Exception as e:
            self.logger.error(f"Monitoring error: {e}")
        finally:
            self.display_summary()
            if self.conn and self.conn.is_connected():
                self.conn.disconnect()
                self.logger.info("Disconnected from ActiveMQ")


# Typer CLI Application
app = typer.Typer(help="Fast Monitoring Client for ePIC SWF Testbed")


@app.command()
def start(
    host: str = typer.Option("localhost", "--host", "-h", help="ActiveMQ host"),
    port: int = typer.Option(61612, "--port", "-p", help="ActiveMQ STOMP port"),
    user: str = typer.Option("admin", "--user", "-u", help="ActiveMQ username"),
    password: str = typer.Option("admin", "--password", help="ActiveMQ password"),
    queue: str = typer.Option("/topic/fastmon_client", "--queue", "-q", help="Topic to subscribe to"),
    ssl: bool = typer.Option(False, "--ssl", help="Use SSL connection"),
    ca_certs: Optional[str] = typer.Option(None, "--ca-certs", help="Path to CA certificates file")
):
    """Start the fast monitoring client."""
    
    # Set environment variables for the client
    os.environ['ACTIVEMQ_HOST'] = host
    os.environ['ACTIVEMQ_PORT'] = str(port)
    os.environ['ACTIVEMQ_USER'] = user
    os.environ['ACTIVEMQ_PASSWORD'] = password
    os.environ['ACTIVEMQ_USE_SSL'] = str(ssl).lower()
    
    if ca_certs:
        os.environ['ACTIVEMQ_SSL_CA_CERTS'] = ca_certs

    # Create and start client
    client = FastMonitoringClient()
    # Override subscription topic if specified
    client.subscription_queue = queue
    
    try:
        client.start_monitoring()
    except Exception as e:
        typer.echo(f"Error starting client: {e}", err=True)
        raise typer.Exit(1)


@app.command()
def status():
    """Show client status and configuration."""
    typer.echo("Fast Monitoring Client Status")
    typer.echo("=" * 40)
    typer.echo(f"ActiveMQ Host: {os.getenv('ACTIVEMQ_HOST', 'localhost')}")
    typer.echo(f"ActiveMQ Port: {os.getenv('ACTIVEMQ_PORT', '61612')}")
    typer.echo(f"Topic: /topic/fastmon_client")
    typer.echo(f"SSL Enabled: {os.getenv('ACTIVEMQ_USE_SSL', 'false')}")


@app.command()
def version():
    """Show client version information."""
    typer.echo("Fast Monitoring Client v1.0.0")
    typer.echo("Part of ePIC SWF Testbed")


if __name__ == "__main__":
    app()
