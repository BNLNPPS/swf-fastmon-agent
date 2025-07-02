from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, Float, ForeignKey, BigInteger, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB, TIMESTAMPTZ
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
import uuid

Base = declarative_base()


class FileStatus(enum.Enum):
    registered = "registered"
    processing = "processing"
    processed = "processed"
    failed = "failed"
    sent_to_mq = "sent_to_mq"


class Run(Base):
    __tablename__ = 'runs'
    
    run_id = Column(Integer, primary_key=True, autoincrement=True)
    run_number = Column(Integer, unique=True, nullable=False)
    start_time = Column(TIMESTAMPTZ, nullable=False)
    end_time = Column(TIMESTAMPTZ)
    run_conditions = Column(JSONB)
    
    stf_files = relationship("StfFile", back_populates="run")


class StfFile(Base):
    __tablename__ = 'stf_files'
    
    file_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id = Column(Integer, ForeignKey('runs.run_id'), nullable=False)
    machine_state = Column(String(64), nullable=False, default="physics")
    file_url = Column(String(1024), unique=True, nullable=False)
    file_size_bytes = Column(BigInteger)
    checksum = Column(String(64))
    creation_time = Column(TIMESTAMPTZ, default=func.current_timestamp())
    status = Column(SQLEnum(FileStatus), nullable=False, default=FileStatus.registered)
    metadata = Column(JSONB)
    
    run = relationship("Run", back_populates="stf_files")
    dispatches = relationship("MessageQueueDispatch", back_populates="stf_file")


class Subscriber(Base):
    __tablename__ = 'subscribers'
    
    subscriber_id = Column(Integer, primary_key=True, autoincrement=True)
    subscriber_name = Column(String(255), unique=True, nullable=False)
    fraction = Column(Float)
    description = Column(Text)
    is_active = Column(Boolean, default=True)


class MessageQueueDispatch(Base):
    __tablename__ = 'message_queue_dispatches'
    
    dispatch_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    file_id = Column(UUID(as_uuid=True), ForeignKey('stf_files.file_id'), nullable=False)
    dispatch_time = Column(TIMESTAMPTZ, nullable=False, default=func.current_timestamp())
    message_content = Column(JSONB)
    is_successful = Column(Boolean, nullable=False)
    error_message = Column(Text)
    
    stf_file = relationship("StfFile", back_populates="dispatches")