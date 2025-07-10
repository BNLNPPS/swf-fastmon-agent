"""
Django models for the SWF Fast Monitoring Agent database.

This module defines the core data models for tracking Super Time Frame (STF) files, message queue subscribers,
and dispatch operations in the ePIC streaming workflow testbed.
"""

from django.db import models
import uuid


class FileStatus(models.TextChoices):
    """
    Status choices for STF file processing lifecycle.
    Tracks the processing state of Super Time Frame files from initial registration through final message queue dispatch.

    Registered: file added to the DB
    Processing: Any pre-treatment before dispatching to MQ
    Processed: Pre-treatment complete, ready to dispatch
    Done: sent to MQ
    Failed: Some problem in the workflow
    """

    REGISTERED = "registered", "Registered"
    PROCESSING = "processing", "Processing"
    PROCESSED = "processed", "Processed"
    FAILED = "failed", "Failed"
    DONE = "done", "Done"


class Run(models.Model):
    """
    Represents a data-taking run in the ePIC detector system.

    Attributes:
        run_id: Auto-incrementing primary key
        run_number: Unique identifier for the run, defined by DAQ
        start_time: When the run began
        end_time: When the run ended (null if still active)
        run_conditions: JSON field storing experimental conditions
    """

    run_id = models.AutoField(primary_key=True)
    run_number = models.IntegerField(unique=True)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField(null=True, blank=True)
    run_conditions = models.JSONField(null=True, blank=True)

    class Meta:
        db_table = "runs"

    def __str__(self):
        return f"Run {self.run_number}"


class StfFile(models.Model):
    """
    Represents a Super Time Frame (STF) file in the data acquisition system.
    Each file is tracked with metadata, processing status, and location
    information for monitoring and message queue dispatch.

    Attributes:
        file_id: UUID primary key for unique file identification
        run: Foreign key to the associated Run
        machine_state: Detector state during data collection (e.g., "physics", "cosmics")
        file_url: URL location of the STF file, intended for remote access
        file_size_bytes: Size of the file in bytes
        checksum: File integrity checksum
        creation_time: Timestamp when file record was created
        status: Current processing status (FileStatus enum)
        metadata: JSON field for additional file metadata
    """

    file_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    run = models.ForeignKey(Run, on_delete=models.CASCADE, related_name="stf_files")
    machine_state = models.CharField(max_length=64, default="physics")
    file_url = models.URLField(max_length=1024, unique=True)
    file_size_bytes = models.BigIntegerField(null=True, blank=True)
    checksum = models.CharField(max_length=64, null=True, blank=True)
    creation_time = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=20, choices=FileStatus.choices, default=FileStatus.REGISTERED
    )
    metadata = models.JSONField(null=True, blank=True)

    class Meta:
        db_table = "stf_files"

    def __str__(self):
        return f"STF File {self.file_id}"


class Subscriber(models.Model):
    """
    Represents a message queue subscriber in the monitoring system. Subscribers receive notifications about STF files.

    Attributes:
        subscriber_id: Auto-incrementing primary key
        subscriber_name: Unique name identifying the subscriber
        fraction: Fraction of messages to receive
        description: Human-readable description of the subscriber
        is_active: Whether the subscriber is currently active
    """

    subscriber_id = models.AutoField(primary_key=True)
    subscriber_name = models.CharField(max_length=255, unique=True)
    fraction = models.FloatField(null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "subscribers"

    def __str__(self):
        return self.subscriber_name


class MessageQueueDispatch(models.Model):
    """
    Records message queue dispatch operations for STF file events.

    Tracks when and how STF file notifications are sent to message queues, including success/failure status and error
    details for monitoring.

    Attributes:
        dispatch_id: UUID primary key for unique dispatch identification
        stf_file: Foreign key to the associated STF file
        dispatch_time: Timestamp when the dispatch occurred
        message_content: JSON content of the dispatched message
        is_successful: Whether the dispatch succeeded
        error_message: Error details if dispatch failed
    """

    dispatch_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    stf_file = models.ForeignKey(
        StfFile, on_delete=models.CASCADE, related_name="dispatches"
    )
    dispatch_time = models.DateTimeField(auto_now_add=True)
    message_content = models.JSONField(null=True, blank=True)
    is_successful = models.BooleanField(null=True, default=None)
    error_message = models.TextField(null=True, blank=True)

    class Meta:
        db_table = "message_queue_dispatches"

    def __str__(self):
        return f"Dispatch {self.dispatch_id}"
