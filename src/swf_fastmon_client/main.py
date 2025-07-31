#!/usr/bin/env python3
"""
SWF Fast Monitoring Client

Client application that receives Time Frame (TF) metadata from the swf-fastmon-agent
via ActiveMQ and stores it in a Django-managed database for monitoring.

This client is designed to be lightweight and portable, allowing remote monitoring
of the ePIC data acquisition system with minimal infrastructure requirements.
"""

import logging
import json
import ssl
import time
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
import typer
import stomp

# Django setup
import django
from django.conf import settings
from django.db import transaction
from django.utils import timezone

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

app = typer.Typer(help="SWF Fast Monitoring Client")


def setup_django_environment(database_config: Dict[str, Any]):
    """Configure Django environment for standalone operation."""
    if not settings.configured:
        settings.configure(
            DEBUG=True,
            DATABASES={
                'default': database_config
            },
            INSTALLED_APPS=[
                'django.contrib.contenttypes',
                'django.contrib.auth',
                'swf-fastmon-client',
            ],
            USE_TZ=True,
            SECRET_KEY='fastmon-client-secret-key-for-standalone-use',
        )
        django.setup()


class FastMonClientDatabase:
    """Django ORM-based database manager for TF metadata storage."""

    def __init__(self, database_config: Dict[str, Any]):
        """Initialize Django environment and database connection."""
        setup_django_environment(database_config)
        
        # Import models after Django is configured
        from .models import TfMetadata, Run
        self.TfMetadata = TfMetadata
        self.Run = Run
        
        self.ensure_tables_exist()

    def ensure_tables_exist(self):
        """Ensure database tables exist by running migrations if needed."""
        from django.core.management import execute_from_command_line
        from django.db import connection
        
        # Check if tables exist
        table_names = connection.introspection.table_names()
        if 'tf_metadata' not in table_names or 'runs' not in table_names:
            logger.info("Creating database tables...")
            execute_from_command_line(['manage.py', 'migrate', '--run-syncdb'])

    def store_tf_metadata(self, tf_data: Dict[str, Any]):
        """Store TF metadata in the database using Django ORM."""
        try:
            with transaction.atomic():
                # Extract common fields from TF data
                file_id = tf_data.get('file_id')
                run_number = tf_data.get('run_number')
                tf_number = tf_data.get('tf_number')
                file_url = tf_data.get('file_url')
                file_size_bytes = tf_data.get('file_size_bytes')
                checksum = tf_data.get('checksum')
                status = tf_data.get('status')
                created_at_str = tf_data.get('created_at')
                
                # Parse created_at timestamp
                created_at = None
                if created_at_str:
                    try:
                        created_at = timezone.datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                    except ValueError:
                        logger.warning(f"Could not parse created_at timestamp: {created_at_str}")
                
                metadata_json = json.dumps(tf_data)

                # Create or update TF metadata
                tf_metadata, created = self.TfMetadata.objects.update_or_create(
                    file_id=file_id,
                    defaults={
                        'run_number': run_number,
                        'tf_number': tf_number,
                        'file_url': file_url,
                        'file_size_bytes': file_size_bytes,
                        'checksum': checksum,
                        'status': status,
                        'created_at': created_at,
                        'metadata_json': metadata_json,
                    }
                )

                # Update run statistics
                if run_number:
                    run_obj, run_created = self.Run.objects.get_or_create(
                        run_number=run_number,
                        defaults={
                            'start_time': timezone.now(),
                            'total_tfs': 0,
                        }
                    )
                    
                    # Update total TF count for the run
                    tf_count = self.TfMetadata.objects.filter(run_number=run_number).count()
                    run_obj.total_tfs = tf_count
                    run_obj.save()

                action = "Created" if created else "Updated"
                logger.info(f"{action} TF metadata: file_id={file_id}, run={run_number}")

        except Exception as e:
            logger.error(f"Error storing TF metadata: {e}")

    def get_run_summary(self, run_number: Optional[int] = None) -> Dict[str, Any]:
        """Get summary statistics for runs using Django ORM."""
        try:
            from django.db.models import Count, Sum, Min, Max
            
            if run_number:
                # Get specific run information
                try:
                    run_obj = self.Run.objects.get(run_number=run_number)
                    run_data = {
                        'run_number': run_obj.run_number,
                        'start_time': run_obj.start_time.isoformat() if run_obj.start_time else None,
                        'end_time': run_obj.end_time.isoformat() if run_obj.end_time else None,
                        'total_tfs': run_obj.total_tfs,
                        'run_conditions': run_obj.run_conditions,
                    }
                except self.Run.DoesNotExist:
                    run_data = None
                
                # Get TF statistics for the run
                tf_stats = self.TfMetadata.objects.filter(run_number=run_number).aggregate(
                    tf_count=Count('id'),
                    first_tf=Min('created_at'),
                    last_tf=Max('created_at'),
                    total_size=Sum('file_size_bytes')
                )
                
                # Convert datetime objects to ISO strings
                if tf_stats['first_tf']:
                    tf_stats['first_tf'] = tf_stats['first_tf'].isoformat()
                if tf_stats['last_tf']:
                    tf_stats['last_tf'] = tf_stats['last_tf'].isoformat()
                
                return {
                    'run': run_data,
                    'stats': tf_stats
                }
            else:
                # Get summary of recent runs
                runs_data = []
                runs = self.Run.objects.order_by('-run_number')[:10]
                
                for run_obj in runs:
                    total_size = self.TfMetadata.objects.filter(
                        run_number=run_obj.run_number
                    ).aggregate(total_size=Sum('file_size_bytes'))['total_size']
                    
                    runs_data.append({
                        'run_number': run_obj.run_number,
                        'start_time': run_obj.start_time.isoformat() if run_obj.start_time else None,
                        'total_tfs': run_obj.total_tfs,
                        'total_size': total_size,
                    })
                
                return {'runs': runs_data}
                
        except Exception as e:
            logger.error(f"Error getting run summary: {e}")
            return {}


class ActiveMQListener(stomp.ConnectionListener):
    """ActiveMQ message listener for TF metadata."""

    def __init__(self, database: FastMonClientDatabase):
        self.database = database

    def on_connected(self, frame):
        """Handle successful connection to ActiveMQ."""
        logger.info("Connected to ActiveMQ broker")

    def on_message(self, frame):
        """Handle incoming TF metadata messages."""
        try:
            logger.debug(f"Received message: {frame.body}")
            tf_data = json.loads(frame.body)
            
            # Validate message has required fields
            if 'file_id' in tf_data:
                self.database.store_tf_metadata(tf_data)
            else:
                logger.warning(f"Message missing required field 'file_id': {frame.body}")

        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode JSON message: {e}")
        except Exception as e:
            logger.error(f"Error processing message: {e}")

    def on_error(self, frame):
        """Handle ActiveMQ errors."""
        logger.error(f"ActiveMQ error: {frame.body}")

    def on_disconnected(self):
        """Handle disconnection from ActiveMQ."""
        logger.warning("Disconnected from ActiveMQ")


class FastMonitoringClient:
    """Main client class for fast monitoring."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize the monitoring client."""
        self.config = config
        self.database = FastMonClientDatabase(config['database_config'])
        self.connection = None
        self.running = False

    def connect_activemq(self) -> bool:
        """Establish connection to ActiveMQ."""
        try:
            host = self.config['activemq_host']
            port = self.config['activemq_port']
            
            self.connection = stomp.Connection([(host, port)])
            
            # Configure SSL if enabled
            if self.config.get('activemq_use_ssl', False):
                ca_certs = self.config.get('activemq_ssl_ca_certs')
                if ca_certs:
                    self.connection.transport.set_ssl(
                        for_hosts=[(host, port)],
                        ca_certs=ca_certs,
                        ssl_version=ssl.PROTOCOL_TLS_CLIENT
                    )
                    logger.info("SSL configured for ActiveMQ connection")

            # Set up message listener
            listener = ActiveMQListener(self.database)
            self.connection.set_listener('', listener)

            # Connect with credentials
            self.connection.connect(
                login=self.config['activemq_user'],
                passcode=self.config['activemq_password'],
                wait=True
            )

            # Subscribe to TF metadata topic
            topic = self.config['activemq_tf_topic']
            self.connection.subscribe(
                destination=topic,
                id='fastmon-client',
                ack='auto'
            )

            logger.info(f"Successfully connected and subscribed to {topic}")
            return True

        except Exception as e:
            logger.error(f"Failed to connect to ActiveMQ: {e}")
            return False

    def start_monitoring(self):
        """Start the monitoring client."""
        logger.info("Starting Fast Monitoring Client...")
        
        if not self.connect_activemq():
            logger.error("Failed to establish ActiveMQ connection")
            return

        self.running = True
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
        finally:
            self.stop_monitoring()

    def stop_monitoring(self):
        """Stop the monitoring client."""
        logger.info("Stopping Fast Monitoring Client...")
        self.running = False
        
        if self.connection and self.connection.is_connected():
            self.connection.disconnect()
            logger.info("Disconnected from ActiveMQ")


@app.command()
def start(
    config_file: Optional[Path] = typer.Option(None, "--config", "-c", help="Configuration file path"),
    db_engine: str = typer.Option("sqlite", "--db-engine", help="Database engine (sqlite, postgresql, mysql)"),
    db_name: str = typer.Option("fastmon_client.db", "--db-name", help="Database name or SQLite file path"),
    db_host: str = typer.Option("localhost", "--db-host", help="Database host"),
    db_port: str = typer.Option("", "--db-port", help="Database port"),
    db_user: str = typer.Option("", "--db-user", help="Database username"),
    db_password: str = typer.Option("", "--db-password", help="Database password"),
    activemq_host: str = typer.Option("localhost", "--host", help="ActiveMQ host"),
    activemq_port: int = typer.Option(61613, "--port", help="ActiveMQ port"),
    activemq_topic: str = typer.Option("epic.fastmon.tf", "--topic", help="ActiveMQ topic for TF metadata"),
    activemq_user: str = typer.Option("admin", "--user", help="ActiveMQ username"),
    activemq_password: str = typer.Option("admin", "--password", help="ActiveMQ password"),
    use_ssl: bool = typer.Option(False, "--ssl", help="Use SSL connection"),
    ca_certs: Optional[str] = typer.Option(None, "--ca-certs", help="Path to CA certificates file"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose logging")
):
    """Start the fast monitoring client."""
    
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Configure database based on engine type
    if db_engine.lower() == 'sqlite':
        database_config = {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': db_name,
        }
    elif db_engine.lower() == 'postgresql':
        database_config = {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': db_name,
            'USER': db_user,
            'PASSWORD': db_password,
            'HOST': db_host,
            'PORT': db_port or '5432',
        }
    elif db_engine.lower() == 'mysql':
        database_config = {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': db_name,
            'USER': db_user,
            'PASSWORD': db_password,
            'HOST': db_host,
            'PORT': db_port or '3306',
        }
    else:
        typer.echo(f"Unsupported database engine: {db_engine}")
        raise typer.Exit(1)

    # Load configuration
    config = {
        'database_config': database_config,
        'activemq_host': activemq_host,
        'activemq_port': activemq_port,
        'activemq_tf_topic': activemq_topic,
        'activemq_user': activemq_user,
        'activemq_password': activemq_password,
        'activemq_use_ssl': use_ssl,
        'activemq_ssl_ca_certs': ca_certs
    }

    # TODO: Add config file support
    if config_file and config_file.exists():
        logger.info(f"Loading configuration from {config_file}")
        # Implementation for config file loading would go here

    # Create and start client
    client = FastMonitoringClient(config)
    client.start_monitoring()


@app.command()
def status(
    db_engine: str = typer.Option("sqlite", "--db-engine", help="Database engine (sqlite, postgresql, mysql)"),
    db_name: str = typer.Option("fastmon_client.db", "--db-name", help="Database name or SQLite file path"),
    db_host: str = typer.Option("localhost", "--db-host", help="Database host"),
    db_port: str = typer.Option("", "--db-port", help="Database port"),
    db_user: str = typer.Option("", "--db-user", help="Database username"),
    db_password: str = typer.Option("", "--db-password", help="Database password"),
    run_number: Optional[int] = typer.Option(None, "--run", help="Specific run number to show")
):
    """Show monitoring status and statistics."""
    
    # Configure database based on engine type
    if db_engine.lower() == 'sqlite':
        database_config = {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': db_name,
        }
        if not Path(db_name).exists():
            typer.echo(f"Database file not found: {db_name}")
            raise typer.Exit(1)
    elif db_engine.lower() == 'postgresql':
        database_config = {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': db_name,
            'USER': db_user,
            'PASSWORD': db_password,
            'HOST': db_host,
            'PORT': db_port or '5432',
        }
    elif db_engine.lower() == 'mysql':
        database_config = {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': db_name,
            'USER': db_user,
            'PASSWORD': db_password,
            'HOST': db_host,
            'PORT': db_port or '3306',
        }
    else:
        typer.echo(f"Unsupported database engine: {db_engine}")
        raise typer.Exit(1)

    database = FastMonClientDatabase(database_config)
    summary = database.get_run_summary(run_number)

    if run_number:
        run_info = summary.get('run')
        stats = summary.get('stats')
        
        if run_info:
            typer.echo(f"Run {run_number}:")
            typer.echo(f"  Start Time: {run_info['start_time']}")
            typer.echo(f"  Total TFs: {run_info['total_tfs']}")
            
            if stats:
                typer.echo(f"  First TF: {stats['first_tf']}")
                typer.echo(f"  Last TF: {stats['last_tf']}")
                typer.echo(f"  Total Size: {stats['total_size']} bytes")
        else:
            typer.echo(f"Run {run_number} not found")
    else:
        runs = summary.get('runs', [])
        if runs:
            typer.echo("Recent Runs:")
            typer.echo("Run Number | Start Time          | TFs  | Total Size")
            typer.echo("-" * 55)
            for run in runs:
                size_mb = (run['total_size'] or 0) / 1024 / 1024
                typer.echo(f"{run['run_number']:10} | {run['start_time']:19} | {run['total_tfs']:4} | {size_mb:.1f} MB")
        else:
            typer.echo("No runs found in database")


@app.command()
def init_db(
    db_engine: str = typer.Option("sqlite", "--db-engine", help="Database engine (sqlite, postgresql, mysql)"),
    db_name: str = typer.Option("fastmon_client.db", "--db-name", help="Database name or SQLite file path"),
    db_host: str = typer.Option("localhost", "--db-host", help="Database host"),
    db_port: str = typer.Option("", "--db-port", help="Database port"),
    db_user: str = typer.Option("", "--db-user", help="Database username"),
    db_password: str = typer.Option("", "--db-password", help="Database password"),
):
    """Initialize the database."""
    
    # Configure database based on engine type
    if db_engine.lower() == 'sqlite':
        database_config = {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': db_name,
        }
        db_path = Path(db_name)
        if db_path.exists():
            if not typer.confirm(f"Database {db_name} already exists. Recreate?"):
                raise typer.Exit()
            db_path.unlink()
    elif db_engine.lower() == 'postgresql':
        database_config = {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': db_name,
            'USER': db_user,
            'PASSWORD': db_password,
            'HOST': db_host,
            'PORT': db_port or '5432',
        }
    elif db_engine.lower() == 'mysql':
        database_config = {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': db_name,
            'USER': db_user,
            'PASSWORD': db_password,
            'HOST': db_host,
            'PORT': db_port or '3306',
        }
    else:
        typer.echo(f"Unsupported database engine: {db_engine}")
        raise typer.Exit(1)

    database = FastMonClientDatabase(database_config)
    typer.echo(f"Database initialized with {db_engine} engine")


if __name__ == "__main__":
    app()