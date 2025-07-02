from django.db import models
import uuid


class FileStatus(models.TextChoices):
    REGISTERED = "registered", "Registered"
    PROCESSING = "processing", "Processing"
    PROCESSED = "processed", "Processed"
    FAILED = "failed", "Failed"
    SENT_TO_MQ = "sent_to_mq", "Sent to MQ"


class Run(models.Model):
    run_id = models.AutoField(primary_key=True)
    run_number = models.IntegerField(unique=True)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField(null=True, blank=True)
    run_conditions = models.JSONField(null=True, blank=True)

    class Meta:
        db_table = 'runs'

    def __str__(self):
        return f"Run {self.run_number}"


class StfFile(models.Model):
    file_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    run = models.ForeignKey(Run, on_delete=models.CASCADE, related_name='stf_files')
    machine_state = models.CharField(max_length=64, default="physics")
    file_url = models.URLField(max_length=1024, unique=True)
    file_size_bytes = models.BigIntegerField(null=True, blank=True)
    checksum = models.CharField(max_length=64, null=True, blank=True)
    creation_time = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=20,
        choices=FileStatus.choices,
        default=FileStatus.REGISTERED
    )
    metadata = models.JSONField(null=True, blank=True)

    class Meta:
        db_table = 'stf_files'

    def __str__(self):
        return f"STF File {self.file_id}"


class Subscriber(models.Model):
    subscriber_id = models.AutoField(primary_key=True)
    subscriber_name = models.CharField(max_length=255, unique=True)
    fraction = models.FloatField(null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'subscribers'

    def __str__(self):
        return self.subscriber_name


class MessageQueueDispatch(models.Model):
    dispatch_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    stf_file = models.ForeignKey(StfFile, on_delete=models.CASCADE, related_name='dispatches')
    dispatch_time = models.DateTimeField(auto_now_add=True)
    message_content = models.JSONField(null=True, blank=True)
    is_successful = models.BooleanField()
    error_message = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'message_queue_dispatches'

    def __str__(self):
        return f"Dispatch {self.dispatch_id}"