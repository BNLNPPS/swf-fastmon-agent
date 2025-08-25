#!/usr/bin/env python3
"""
Unit tests for fastmon_utils.py REST API functions.
"""

import pytest
import logging
from unittest.mock import Mock, MagicMock, patch
from pathlib import Path
from datetime import datetime
import tempfile
import os

from swf_fastmon_agent.fastmon_utils import (
    get_or_create_run,
    record_stf_file,
    simulate_tf_subsamples,
    record_tf_file,
    FileStatus
)


class TestGetOrCreateRun:
    """Tests for get_or_create_run function."""

    def test_get_existing_run(self):
        """Test getting an existing run via REST API."""
        # Mock agent and logger
        mock_agent = Mock()
        mock_logger = Mock()
        
        # Mock API response for existing run
        mock_agent.call_monitor_api.return_value = {
            'results': [{'run_id': 123, 'run_number': 42, 'start_time': '2023-01-01T00:00:00Z'}]
        }
        
        result = get_or_create_run(42, mock_agent, mock_logger)
        
        # Verify API call was made correctly
        mock_agent.call_monitor_api.assert_called_once_with('get', '/runs/?run_number=42')
        assert result['run_id'] == 123
        assert result['run_number'] == 42

    def test_create_new_run(self):
        """Test creating a new run via REST API when it doesn't exist."""
        # Mock agent and logger
        mock_agent = Mock()
        mock_logger = Mock()
        
        # Mock API responses - first call returns no results, second creates new run
        mock_agent.call_monitor_api.side_effect = [
            {'results': []},  # No existing run found
            {'run_id': 456, 'run_number': 99, 'start_time': '2023-01-01T00:00:00Z'}  # New run created
        ]
        
        result = get_or_create_run(99, mock_agent, mock_logger)
        
        # Verify both API calls were made
        assert mock_agent.call_monitor_api.call_count == 2
        mock_agent.call_monitor_api.assert_any_call('get', '/runs/?run_number=99')
        
        # Check the POST call
        post_call = mock_agent.call_monitor_api.call_args_list[1]
        assert post_call[0][0] == 'post'
        assert post_call[0][1] == '/runs/'
        assert post_call[0][2]['run_number'] == 99
        assert 'auto_created' in post_call[0][2]['run_conditions']


class TestRecordFile:
    """Tests for record_file function."""

    def test_record_new_file(self):
        """Test recording a new STF file via REST API."""
        # Create a temporary file for testing
        with tempfile.NamedTemporaryFile(suffix='.stf', delete=False) as tf:
            tf.write(b'test data')
            temp_file_path = Path(tf.name)
        
        try:
            # Mock agent and logger
            mock_agent = Mock()
            mock_logger = Mock()
            
            # Mock API responses
            mock_agent.call_monitor_api.side_effect = [
                {'results': []},  # File doesn't exist
                {'run_id': 123, 'run_number': 1},  # Run data
                {'file_id': 'uuid-123', 'stf_filename': temp_file_path.name}  # STF file created
            ]
            
            config = {
                'base_url': 'file://',
                'default_run_number': 1,
                'calculate_checksum': False
            }
            
            # Mock get_or_create_run
            with patch('swf_fastmon_agent.fastmon_utils.get_or_create_run') as mock_get_run:
                mock_get_run.return_value = {'run_id': 123, 'run_number': 1}
                
                result = record_stf_file(temp_file_path, config, mock_agent, mock_logger)
            
            # Verify file was recorded
            assert result['file_id'] == 'uuid-123'
            assert mock_agent.call_monitor_api.call_count >= 2
            
        finally:
            # Clean up temporary file
            if temp_file_path.exists():
                temp_file_path.unlink()

    def test_record_existing_file(self):
        """Test handling of already recorded files."""
        temp_file_path = Path('/tmp/test.stf')
        
        # Mock agent and logger
        mock_agent = Mock()
        mock_logger = Mock()
        
        # Mock API response for existing file
        mock_agent.call_monitor_api.return_value = {
            'results': [{'file_id': 'existing-uuid', 'stf_filename': 'test.stf'}]
        }
        
        config = {'base_url': 'file://', 'default_run_number': 1}
        
        result = record_stf_file(temp_file_path, config, mock_agent, mock_logger)
        
        # Should return existing file without creating new one
        assert result['file_id'] == 'existing-uuid'
        mock_agent.call_monitor_api.assert_called_once()


class TestSimulateTfSubsamples:
    """Tests for simulate_tf_subsamples function."""

    def test_generate_tf_subsamples(self):
        """Test generating TF subsamples from STF file."""
        mock_logger = Mock()
        
        stf_file = {
            'file_id': 'stf-uuid-123',
            'stf_filename': 'test_run001.stf',
            'file_size_bytes': 1000000
        }
        
        file_path = Path('/tmp/test_run001.stf')
        
        config = {
            'tf_files_per_stf': 3,
            'tf_size_fraction': 0.2,
            'tf_sequence_start': 1,
            'agent_name': 'test-agent'
        }
        
        result = simulate_tf_subsamples(stf_file, file_path, config, mock_logger)
        
        # Verify correct number of TF files generated
        assert len(result) == 3
        
        # Verify TF file structure
        for i, tf in enumerate(result):
            assert 'tf_filename' in tf
            assert 'file_size_bytes' in tf
            assert 'sequence_number' in tf
            assert tf['sequence_number'] == i + 1
            assert tf['stf_parent'] == 'stf-uuid-123'
            assert 'simulation' in tf['metadata']

    def test_generate_tf_with_defaults(self):
        """Test TF generation with default configuration values."""
        mock_logger = Mock()
        
        stf_file = {
            'file_id': 'stf-uuid-456',
            'stf_filename': 'test.stf',
            'file_size_bytes': 500000
        }
        
        file_path = Path('/tmp/test.stf')
        config = {}  # Empty config to test defaults
        
        result = simulate_tf_subsamples(stf_file, file_path, config, mock_logger)
        
        # Should use default values (7 TF files)
        assert len(result) == 7
        
        # Verify default sequence numbering
        assert result[0]['sequence_number'] == 1
        assert result[-1]['sequence_number'] == 7


class TestRecordTfFile:
    """Tests for record_tf_file function."""

    def test_record_tf_file_success(self):
        """Test successful TF file recording via REST API."""
        # Mock agent and logger
        mock_agent = Mock()
        mock_logger = Mock()
        
        # Mock API response for successful creation
        mock_agent.call_monitor_api.return_value = {
            'tf_file_id': 'tf-uuid-123',
            'tf_filename': 'test_tf_001.tf',
            'status': 'REGISTERED'
        }
        
        stf_file = {'file_id': 'stf-uuid-123'}
        tf_metadata = {
            'tf_filename': 'test_tf_001.tf',
            'file_size_bytes': 150000,
            'metadata': {'simulation': True}
        }
        config = {}
        
        result = record_tf_file(stf_file, tf_metadata, config, mock_agent, mock_logger)
        
        # Verify TF file was recorded
        assert result['tf_file_id'] == 'tf-uuid-123'
        mock_agent.call_monitor_api.assert_called_once_with('post', '/fastmon-files/', {
            'stf_file': 'stf-uuid-123',
            'tf_filename': 'test_tf_001.tf',
            'file_size_bytes': 150000,
            'status': FileStatus.REGISTERED,
            'metadata': {'simulation': True}
        })

    def test_record_tf_file_failure(self):
        """Test handling of TF file recording failure."""
        # Mock agent and logger
        mock_agent = Mock()
        mock_logger = Mock()
        
        # Mock API call that raises exception
        mock_agent.call_monitor_api.side_effect = Exception("API Error")
        
        stf_file = {'file_id': 'stf-uuid-123'}
        tf_metadata = {
            'tf_filename': 'test_tf_001.tf',
            'file_size_bytes': 150000
        }
        config = {}
        
        result = record_tf_file(stf_file, tf_metadata, config, mock_agent, mock_logger)
        
        # Should return None on failure
        assert result is None
        mock_logger.error.assert_called_once()