#!/usr/bin/env python3
"""
Unit tests for fastmon_utils.py
"""

import pytest
import logging
import tempfile
import hashlib
from pathlib import Path
from unittest.mock import Mock, patch

# Django test utilities
from django.test import TestCase
from django.utils import timezone

# Import the functions to test
from swf_fastmon_agent.agents.fastmon_utils import (
    setup_logging,
    validate_config,
    find_recent_files,
    select_files,
    extract_run_number,
    calculate_checksum,
    construct_file_url,
    get_or_create_run,
    record_file
)

# Django models
from swf_fastmon_agent.database.models import Run, StfFile, FileStatus


class TestSetupLogging:
    """Test the setup_logging function"""
    
    def test_setup_logging_default(self):
        """Test setup_logging with default parameters"""
        logger = setup_logging()
        assert logger.name == 'swf_fastmon_agent.file_monitor'
        assert logger.level == logging.INFO
        assert len(logger.handlers) == 1
        
    def test_setup_logging_custom_name(self):
        """Test setup_logging with custom logger name"""
        logger = setup_logging('test_logger')
        assert logger.name == 'test_logger'
        assert logger.level == logging.INFO
        
    def test_setup_logging_no_duplicate_handlers(self):
        """Test that multiple calls don't create duplicate handlers"""
        logger1 = setup_logging('test_logger_unique')
        logger2 = setup_logging('test_logger_unique')
        assert len(logger1.handlers) == 1
        assert len(logger2.handlers) == 1


class TestValidateConfig:
    """Test the validate_config function"""

    def test_validate_config_valid(self):
        """Test validate_config with valid configuration"""
        config = {
            'watch_directories': ['/tmp'],
            'file_patterns': ['*.stf'],
            'check_interval': 60,
            'lookback_time': 10,
            'selection_fraction': 0.5,
            'default_run_number': 1000
        }
        validate_config(config)  # Should not raise

    def test_validate_config_missing_key(self):
        """Test validate_config with missing required key"""
        config = {
            'watch_directories': ['/tmp'],
            'file_patterns': ['*.stf'],
            'check_interval': 60,
            'lookback_time': 10,
            'selection_fraction': 0.5
            # Missing default_run_number
        }
        with pytest.raises(ValueError, match="Missing required configuration key: default_run_number"):
            validate_config(config)

    def test_validate_config_invalid_fraction(self):
        """Test validate_config with invalid selection fraction"""
        config = {
            'watch_directories': ['/tmp'],
            'file_patterns': ['*.stf'],
            'check_interval': 60,
            'lookback_time': 10,
            'selection_fraction': 1.5,  # Invalid
            'default_run_number': 1000
        }
        with pytest.raises(ValueError, match="selection_fraction must be between 0.0 and 1.0"):
            validate_config(config)


class TestFindRecentFiles:
    """Test the find_recent_files function"""

    def test_find_recent_files_no_lookback(self):
        """Test find_recent_files with no lookback time"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test files
            test_file = Path(temp_dir) / "test.stf"
            test_file.write_text("test content")

            config = {
                'watch_directories': [temp_dir],
                'file_patterns': ['*.stf'],
                'lookback_time': None
            }
            logger = Mock()

            files = find_recent_files(config, logger)
            assert len(files) == 1
            assert files[0].name == "test.stf"

    def test_find_recent_files_with_lookback(self):
        """Test find_recent_files with lookback time"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test files
            test_file = Path(temp_dir) / "test.stf"
            test_file.write_text("test content")

            config = {
                'watch_directories': [temp_dir],
                'file_patterns': ['*.stf'],
                'lookback_time': 60  # 60 minutes
            }
            logger = Mock()

            files = find_recent_files(config, logger)
            assert len(files) == 1

    def test_find_recent_files_nonexistent_directory(self):
        """Test find_recent_files with non-existent directory"""
        config = {
            'watch_directories': ['/nonexistent/path'],
            'file_patterns': ['*.stf'],
            'lookback_time': 60
        }
        logger = Mock()

        files = find_recent_files(config, logger)
        assert len(files) == 0
        logger.warning.assert_called_once()


class TestSelectFiles:
    """Test the select_files function"""

    def test_select_files_empty_list(self):
        """Test select_files with empty file list"""
        logger = Mock()
        result = select_files([], 0.5, logger)
        assert result == []

    def test_select_files_fraction(self):
        """Test select_files with fraction selection"""
        files = [Path(f"/tmp/file{i}.stf") for i in range(10)]
        logger = Mock()

        result = select_files(files, 0.5, logger)
        assert len(result) == 5
        assert all(f in files for f in result)

    def test_select_files_min_one(self):
        """Test select_files always selects at least one file"""
        files = [Path("/tmp/file1.stf")]
        logger = Mock()

        result = select_files(files, 0.1, logger)
        assert len(result) == 1

    @patch('swf_fastmon_agent.agents.fastmon_utils.random.sample')
    def test_select_files_random_called(self, mock_random):
        """Test that random.sample is called correctly"""
        files = [Path(f"/tmp/file{i}.stf") for i in range(5)]
        mock_random.return_value = files[:2]
        logger = Mock()

        result = select_files(files, 0.4, logger)
        mock_random.assert_called_once_with(files, 2)
        assert result == files[:2]


class TestExtractRunNumber:
    """Test the extract_run_number function"""

    def test_extract_run_number_run_underscore(self):
        """Test extracting run number with run_ pattern"""
        file_path = Path("/tmp/run_12345_stf_001.stf")
        result = extract_run_number(file_path, 9999)
        assert result == 12345

    def test_extract_run_number_run_no_underscore(self):
        """Test extracting run number with run pattern (no underscore)"""
        file_path = Path("/tmp/run12345_stf_001.stf")
        result = extract_run_number(file_path, 9999)
        assert result == 12345

    def test_extract_run_number_r_pattern(self):
        """Test extracting run number with r pattern"""
        file_path = Path("/tmp/r12345_stf_001.stf")
        result = extract_run_number(file_path, 9999)
        assert result == 12345

    def test_extract_run_number_case_insensitive(self):
        """Test extracting run number is case insensitive"""
        file_path = Path("/tmp/RUN_12345_stf_001.stf")
        result = extract_run_number(file_path, 9999)
        assert result == 12345

    def test_extract_run_number_no_match(self):
        """Test extracting run number when no pattern matches"""
        file_path = Path("/tmp/some_file.stf")
        result = extract_run_number(file_path, 9999)
        assert result == 9999


class TestCalculateChecksum:
    """Test the calculate_checksum function"""

    def test_calculate_checksum_valid_file(self):
        """Test calculating checksum for valid file"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("test content")
            f.flush()

            logger = Mock()
            result = calculate_checksum(Path(f.name), logger)

            # Calculate expected checksum
            expected = hashlib.md5(b"test content").hexdigest()
            assert result == expected

        Path(f.name).unlink()  # Clean up

    def test_calculate_checksum_nonexistent_file(self):
        """Test calculating checksum for non-existent file"""
        logger = Mock()
        result = calculate_checksum(Path("/nonexistent/file.stf"), logger)
        assert result == ""
        logger.error.assert_called_once()


class TestConstructFileUrl:
    """Test the construct_file_url function"""

    def test_construct_file_url_default(self):
        """Test constructing file URL with default base"""
        file_path = Path("/tmp/test.stf")
        result = construct_file_url(file_path)
        assert result.startswith("file://")
        assert result.endswith("/tmp/test.stf")

    def test_construct_file_url_custom_base(self):
        """Test constructing file URL with custom base"""
        file_path = Path("/tmp/test.stf")
        result = construct_file_url(file_path, "https://example.com/")
        assert result.startswith("https://example.com")
        assert result.endswith("/tmp/test.stf")

    def test_construct_file_url_base_without_slash(self):
        """Test constructing file URL with base URL without trailing slash"""
        file_path = Path("/tmp/test.stf")
        result = construct_file_url(file_path, "https://example.com")
        assert result.startswith("https://example.com")
        assert result.endswith("/tmp/test.stf")


class TestDjangoFunctions(TestCase):
    """Test Django-dependent functions using Django TestCase"""
    
    def setUp(self):
        """Set up test data"""
        self.logger = Mock()
        
    def test_get_or_create_run_new(self):
        """Test get_or_create_run creates new run"""
        run = get_or_create_run(12345, self.logger)
        
        assert run.run_number == 12345
        assert run.run_conditions == {'auto_created': True}
        assert Run.objects.count() == 1
        self.logger.info.assert_called_with("Created new run: 12345")
        
    def test_get_or_create_run_existing(self):
        """Test get_or_create_run returns existing run"""
        # Create initial run
        existing_run = Run.objects.create(
            run_number=12345,
            start_time=timezone.now(),
            run_conditions={'manual': True}
        )
        
        run = get_or_create_run(12345, self.logger)
        
        assert run.run_id == existing_run.run_id
        assert run.run_conditions == {'manual': True}  # Should keep original
        assert Run.objects.count() == 1
        self.logger.info.assert_not_called()
        
    def test_record_file_new(self):
        """Test record_file creates new STF file record"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("test content")
            f.flush()
            
            file_path = Path(f.name)
            config = {
                'default_run_number': 1000,
                'base_url': 'file://',
                'calculate_checksum': False
            }
            
            record_file(file_path, config, self.logger)
            
            # Check that file was recorded
            assert StfFile.objects.count() == 1
            stf_file = StfFile.objects.first()
            assert stf_file.run.run_number == 1000
            assert stf_file.file_url.startswith('file://')
            assert stf_file.file_url.endswith(f.name)
            assert stf_file.status == FileStatus.REGISTERED
            assert stf_file.file_size_bytes > 0
            
        Path(f.name).unlink()  # Clean up
        
    def test_record_file_existing(self):
        """Test record_file skips existing files"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("test content")
            f.flush()
            
            file_path = Path(f.name)
            config = {
                'default_run_number': 1000,
                'base_url': 'file://',
                'calculate_checksum': False
            }
            
            # Record file twice
            record_file(file_path, config, self.logger)
            record_file(file_path, config, self.logger)
            
            # Should only have one record
            assert StfFile.objects.count() == 1
            
        Path(f.name).unlink()  # Clean up
        
    def test_record_file_with_checksum(self):
        """Test record_file with checksum calculation"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("test content")
            f.flush()
            
            file_path = Path(f.name)
            config = {
                'default_run_number': 1000,
                'base_url': 'file://',
                'calculate_checksum': True
            }
            
            record_file(file_path, config, self.logger)
            
            stf_file = StfFile.objects.first()
            expected_checksum = hashlib.md5(b"test content").hexdigest()
            assert stf_file.checksum == expected_checksum
            
        Path(f.name).unlink()  # Clean up
        
    def test_record_file_with_run_number_extraction(self):
        """Test record_file extracts run number from filename"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='_run_5678_stf.stf', delete=False) as f:
            f.write("test content")
            f.flush()
            
            file_path = Path(f.name)
            config = {
                'default_run_number': 1000,
                'base_url': 'file://',
                'calculate_checksum': False
            }
            
            record_file(file_path, config, self.logger)
            
            stf_file = StfFile.objects.first()
            assert stf_file.run.run_number == 5678
            
        Path(f.name).unlink()  # Clean up