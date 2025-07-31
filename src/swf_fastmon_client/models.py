"""
Django models for the SWF Fast Monitoring Client.

These models represent the data structures used by the fast monitoring client
to store Time Frame (TF) metadata received via ActiveMQ messaging.
"""

import json
from django.db import models
from django.utils import timezone


class Run(models.Model):
    """
    Represents a data-taking run in the fast monitoring client database.
    """
    run_number = models.IntegerField(primary_key=True)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField(null=True, blank=True)
    total_tfs = models.IntegerField(default=0)
    run_conditions = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'runs'

    def __str__(self):
        return f"Run {self.run_number}"


class TfMetadata(models.Model):
    """
    Represents Time Frame (TF) metadata in the fast monitoring client database.
    """
    id = models.AutoField(primary_key=True)
    file_id = models.TextField(unique=True)
    run_number = models.IntegerField()
    tf_number = models.IntegerField(null=True, blank=True)
    file_url = models.TextField(null=True, blank=True)
    file_size_bytes = models.IntegerField(null=True, blank=True)
    checksum = models.TextField(null=True, blank=True)
    status = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(null=True, blank=True)
    received_at = models.DateTimeField(default=timezone.now)
    metadata_json = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'tf_metadata'
        indexes = [
            models.Index(fields=['run_number']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"TF {self.file_id} - Run {self.run_number}"

    def get_metadata_dict(self):
        """Parse the JSON metadata string into a dictionary."""
        if self.metadata_json:
            try:
                return json.loads(self.metadata_json)
            except json.JSONDecodeError:
                return {}
        return {}

    def set_metadata_dict(self, metadata_dict):
        """Convert a dictionary to JSON and store it in metadata_json."""
        if metadata_dict:
            self.metadata_json = json.dumps(metadata_dict)
        else:
            self.metadata_json = None