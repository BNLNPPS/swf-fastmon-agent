from datetime import datetime, timezone
from django.test import TestCase
from swf_fastmon_agent.database.models import FileStatus, Run, StfFile, MessageQueueDispatch

class FastMonitorDBModelsTestCase(TestCase):
    """
    Base test case for fast monitoring DB models.
    """

    @classmethod
    def setUpTestData(cls):
        """
        Set up initial data for the test case.
        """
        # Create a sample run_instance
        cls.run_instance = Run.objects.create(
            run_number=1003,
            start_time=datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
        )

        # Create a sample STF file
        cls.stf_file = StfFile.objects.create(
            run=cls.run_instance,
            machine_state="physics",
            file_url="https://test.bnl.gov/daqsim/test.stf",
            file_size_bytes=1024,
            checksum="98dd0ac3",  # Aider32 for "A test for my fast monitoring"
            metadata={"Collision type": "e-p"}
        )

        # Create a sample message queue dispatch
        cls.message_queue_dispatch = MessageQueueDispatch.objects.create(
            stf_file=cls.stf_file,
            message_content={"message": "A test message for fast monitoring"}
        )

    def test_stf_file_creation(self):
        """
        Trivial test that STF file creation works correctly.
        """
        self.assertEqual(self.stf_file.run, self.run_instance)
        self.assertEqual(self.stf_file.machine_state, "physics")
        self.assertEqual(self.stf_file.file_url, "https://test.bnl.gov/daqsim/test.stf")
        self.assertEqual(self.stf_file.file_size_bytes, 1024)
        self.assertEqual(self.stf_file.checksum, "98dd0ac3")
        self.assertEqual(self.stf_file.metadata["Collision type"], "e-p")

