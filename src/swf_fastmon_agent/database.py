from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from contextlib import contextmanager
from typing import Optional, Dict, Any, List
import os
import logging

from .models import Base, StfFile, Run, FileStatus

logger = logging.getLogger(__name__)


class DatabaseManager:
    def __init__(self, database_url: Optional[str] = None):
        if database_url is None:
            database_url = self._get_database_url_from_env()
        
        self.engine = create_engine(
            database_url,
            poolclass=QueuePool,
            pool_size=5,
            max_overflow=10,
            echo=False
        )
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)


    def _get_database_url_from_env(self) -> str:
        """
        Constructs the database URL from environment variables

        :return: URL string for the connection to the PostgreSQL database
        """
        host = os.getenv('POSTGRES_HOST', 'localhost')
        port = os.getenv('POSTGRES_PORT', '5432')
        database = os.getenv('POSTGRES_DB', 'swf_fastmonitoring')
        user = os.getenv('POSTGRES_USER', 'postgres')
        password = os.getenv('POSTGRES_PASSWORD', '')
        
        return f"postgresql://{user}:{password}@{host}:{port}/{database}"


    def create_tables(self):
        """
        Creates all tables in the database based on the defined models.
        This method should be called once to set up the database schema.
        """
        Base.metadata.create_all(bind=self.engine)


    @contextmanager
    def get_session(self):
        """
        Provides a context manager for database sessions
        """
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()
    
    def insert_stf_file(self, run_id: int, machine_state: str, file_url: str,
                       file_size_bytes: Optional[int] = None, checksum: Optional[str] = None,
                       status: FileStatus = FileStatus.registered, metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Inserts a new STF file record into the database
        :param run_id: ID for the run associated with this STF file
        :param file_url: URL where the STF file is stored
        :param file_size_bytes: Size of the STF file in bytes
        :param checksum: Checksum of the STF file for integrity verification # TODO: Which checksum algorithm?
        :param machine_state: State of the EIC accelerator when the file was created (physics, calibration, debug, etc.)
        :param status: Status of the STF file (default "registered")
        :param metadata: Any additional info in JSON format
        :return:
        """
        with self.get_session() as session:
            stf_file = StfFile(
                run_id=run_id,
                machine_state=machine_state,
                file_url=file_url,
                file_size_bytes=file_size_bytes,
                checksum=checksum,
                status=status,
                metadata=metadata
            )
            session.add(stf_file)
            session.flush()
            file_id = str(stf_file.file_id)
            logger.info(f"Inserted STF file with ID: {file_id}")
            return file_id


    def get_stf_file_metadata(self, file_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves metadata for a specific STF file by its ID

        :return: Dictionary containing file metadata or None if not found
        """
        with self.get_session() as session:
            stf_file = session.query(StfFile).filter(StfFile.file_id == file_id).first()
            if not stf_file:
                return None
            
            return {
                'file_id': str(stf_file.file_id),
                'run_id': stf_file.run_id,
                'stf_identifier': stf_file.stf_identifier,
                'file_url': stf_file.file_url,
                'file_size_bytes': stf_file.file_size_bytes,
                'checksum': stf_file.checksum,
                'creation_time': stf_file.creation_time,
                'status': stf_file.status.value if stf_file.status else None,
                'metadata': stf_file.metadata
            }


    def get_stf_files_by_run(self, run_id: int) -> List[Dict[str, Any]]:
        """
        Retrieves all STF files associated with a specific run ID

        :return: List of dictionaries containing STF file metadata
        """
        with self.get_session() as session:
            stf_files = session.query(StfFile).filter(StfFile.run_id == run_id).all()
            return [
                {
                    'file_id': str(stf_file.file_id),
                    'run_id': stf_file.run_id,
                    'stf_identifier': stf_file.stf_identifier,
                    'file_url': stf_file.file_url,
                    'file_size_bytes': stf_file.file_size_bytes,
                    'checksum': stf_file.checksum,
                    'creation_time': stf_file.creation_time,
                    'status': stf_file.status.value if stf_file.status else None,
                    'metadata': stf_file.metadata
                }
                for stf_file in stf_files
            ]


    def get_stf_files_by_status(self, status: FileStatus) -> List[Dict[str, Any]]:
        """
        Retrieves all STF files with a specific status (e.g., registered, processing, processed, failed)

        :return: List of dictionaries containing STF file metadata
        """
        with self.get_session() as session:
            stf_files = session.query(StfFile).filter(StfFile.status == status).all()
            return [
                {
                    'file_id': str(stf_file.file_id),
                    'run_id': stf_file.run_id,
                    'stf_identifier': stf_file.stf_identifier,
                    'file_url': stf_file.file_url,
                    'file_size_bytes': stf_file.file_size_bytes,
                    'checksum': stf_file.checksum,
                    'creation_time': stf_file.creation_time,
                    'status': stf_file.status.value if stf_file.status else None,
                    'metadata': stf_file.metadata
                }
                for stf_file in stf_files
            ]