import os
import logging
from typing import Optional, Dict, Any, List
from django.conf import settings
from django.core.management import execute_from_command_line
import django

from .models import StfFile, Run, FileStatus

logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    Django-based database manager for STF file operations
    """
    
    def __init__(self):
        self._setup_django()
    
    def _setup_django(self):
        """Configure Django if not already configured"""
        if not settings.configured:
            # Configure Django settings
            settings.configure(
                DATABASES={
                    'default': {
                        'ENGINE': 'django.db.backends.postgresql',
                        'NAME': os.getenv('POSTGRES_DB', 'swf_fastmonitoring'),
                        'USER': os.getenv('POSTGRES_USER', 'postgres'),
                        'PASSWORD': os.getenv('POSTGRES_PASSWORD', 'postgres'),
                        'HOST': os.getenv('POSTGRES_HOST', 'localhost'),
                        'PORT': os.getenv('POSTGRES_PORT', '5432'),
                    }
                },
                INSTALLED_APPS=[
                    'django.contrib.contenttypes',
                    'swf_fastmon_agent.database',
                ],
                USE_TZ=True,
                SECRET_KEY='dev-key-for-database-operations',
            )
            django.setup()
    
    def create_tables(self):
        """
        Creates all tables in the database based on the defined models.
        This method should be called once to set up the database schema.
        """
        from django.core.management import call_command
        call_command('migrate', verbosity=0)
        logger.info("Database tables created successfully!")
    
    def insert_stf_file(self, run_id: int, machine_state: str, file_url: str,
                       file_size_bytes: Optional[int] = None, checksum: Optional[str] = None,
                       status: str = FileStatus.REGISTERED, metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Inserts a new STF file record into the database
        
        :param run_id: ID for the run associated with this STF file
        :param machine_state: State of the EIC accelerator when the file was created
        :param file_url: URL where the STF file is stored
        :param file_size_bytes: Size of the STF file in bytes
        :param checksum: Checksum of the STF file for integrity verification
        :param status: Status of the STF file (default "registered")
        :param metadata: Any additional info in JSON format
        :return: String representation of the file UUID
        """
        try:
            run = Run.objects.get(run_id=run_id)
            stf_file = StfFile.objects.create(
                run=run,
                machine_state=machine_state,
                file_url=file_url,
                file_size_bytes=file_size_bytes,
                checksum=checksum,
                status=status,
                metadata=metadata
            )
            file_id = str(stf_file.file_id)
            logger.info(f"Inserted STF file with ID: {file_id}")
            return file_id
        except Run.DoesNotExist:
            logger.error(f"Run with ID {run_id} does not exist")
            raise ValueError(f"Run with ID {run_id} does not exist")
        except Exception as e:
            logger.error(f"Error inserting STF file: {e}")
            raise
    
    def get_stf_file_metadata(self, file_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves metadata for a specific STF file by its ID
        
        :param file_id: UUID of the STF file
        :return: Dictionary containing file metadata or None if not found
        """
        try:
            stf_file = StfFile.objects.get(file_id=file_id)
            return {
                'file_id': str(stf_file.file_id),
                'run_id': stf_file.run.run_id,
                'machine_state': stf_file.machine_state,
                'file_url': stf_file.file_url,
                'file_size_bytes': stf_file.file_size_bytes,
                'checksum': stf_file.checksum,
                'creation_time': stf_file.creation_time,
                'status': stf_file.status,
                'metadata': stf_file.metadata
            }
        except StfFile.DoesNotExist:
            logger.warning(f"STF file with ID {file_id} not found")
            return None
        except Exception as e:
            logger.error(f"Error retrieving STF file metadata: {e}")
            raise
    
    def get_stf_files_by_run(self, run_id: int) -> List[Dict[str, Any]]:
        """
        Retrieves all STF files associated with a specific run ID
        
        :param run_id: ID of the run
        :return: List of dictionaries containing STF file metadata
        """
        try:
            stf_files = StfFile.objects.filter(run__run_id=run_id).select_related('run')
            return [
                {
                    'file_id': str(stf_file.file_id),
                    'run_id': stf_file.run.run_id,
                    'machine_state': stf_file.machine_state,
                    'file_url': stf_file.file_url,
                    'file_size_bytes': stf_file.file_size_bytes,
                    'checksum': stf_file.checksum,
                    'creation_time': stf_file.creation_time,
                    'status': stf_file.status,
                    'metadata': stf_file.metadata
                }
                for stf_file in stf_files
            ]
        except Exception as e:
            logger.error(f"Error retrieving STF files for run {run_id}: {e}")
            raise
    
    def get_stf_files_by_status(self, status: str) -> List[Dict[str, Any]]:
        """
        Retrieves all STF files with a specific status
        
        :param status: Status of the files to retrieve
        :return: List of dictionaries containing STF file metadata
        """
        try:
            stf_files = StfFile.objects.filter(status=status).select_related('run')
            return [
                {
                    'file_id': str(stf_file.file_id),
                    'run_id': stf_file.run.run_id,
                    'machine_state': stf_file.machine_state,
                    'file_url': stf_file.file_url,
                    'file_size_bytes': stf_file.file_size_bytes,
                    'checksum': stf_file.checksum,
                    'creation_time': stf_file.creation_time,
                    'status': stf_file.status,
                    'metadata': stf_file.metadata
                }
                for stf_file in stf_files
            ]
        except Exception as e:
            logger.error(f"Error retrieving STF files with status {status}: {e}")
            raise
    
    def create_run(self, run_number: int, start_time, end_time=None, run_conditions=None) -> int:
        """
        Creates a new run record
        
        :param run_number: Unique run number
        :param start_time: Start time of the run
        :param end_time: End time of the run (optional)
        :param run_conditions: JSON metadata for run conditions
        :return: Run ID
        """
        try:
            run = Run.objects.create(
                run_number=run_number,
                start_time=start_time,
                end_time=end_time,
                run_conditions=run_conditions
            )
            logger.info(f"Created run {run_number} with ID: {run.run_id}")
            return run.run_id
        except Exception as e:
            logger.error(f"Error creating run: {e}")
            raise