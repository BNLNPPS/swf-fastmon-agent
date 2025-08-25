# SWF Fast Monitoring Agent

**`swf-fastmon-agent`** is a fast monitoring service for the ePIC streaming workflow testbed.

This agent monitors STF (Super Time Frame) files, samples TF (Time Frame) subsets, and distributes metadata via ActiveMQ message queues, enabling real-time remote monitoring of ePIC data acquisition processes. The agent includes both server-side monitoring capabilities and a client for remote visualization.

## Architecture Overview

The fast monitoring agent is designed as part of the **SWF testbed ecosystem** and integrates with:
- **swf-monitor**: PostgreSQL database and Django web interface for persistent monitoring data
- **swf-testbed**: Infrastructure orchestration and process management  
- **swf-common-lib**: Shared utilities and BaseAgent framework for messaging
- **swf-data-agent**: Receiving messages when STF files are available for fast monitoring

The agent operates as a managed service within the swf-testbed ecosystem, automatically configured and monitored through the central CLI. It extends the BaseAgent class from swf-common-lib for consistent messaging and logging across the ecosystem.

-------------- 

## Integration with SWF Testbed

### Prerequisites
- Complete SWF testbed ecosystem (swf-testbed, swf-monitor, swf-common-lib as siblings)
- Docker Desktop for infrastructure services
- Python 3.9+ virtual environment

### Running the Agent
```bash
# The agent runs as a managed service within the testbed
cd $SWF_PARENT_DIR/swf-testbed
swf-testbed status  # Check if fast monitoring agent is running

# Manual development run (message-driven mode - default)
cd ../swf-fastmon-agent
python -m swf_fastmon_agent.main

# Continuous monitoring mode (for testing)
cd ../swf-fastmon-agent
export FASTMON_MODE=continuous 
python -m swf_fastmon_agent.main
```

### Working with Django Models
```python
import django
import os

# Configure Django settings to use swf-monitor database
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'swf_monitor_project.settings')
django.setup()
```

## Agent Configuration

The fast monitoring agent is configured through the swf-testbed ecosystem:

### Environment Variables
- Database connection: Managed by swf-monitor's Django settings
- ActiveMQ connection: Configured via swf-testbed infrastructure
- Logging: Uses swf-common-lib utilities for consistent logging across ecosystem

## Agent Components

### Fast Monitor Agent
- **STF File Monitoring**: Monitors directories for newly created STF files
- **TF Sampling**: Simulates TF subsamples from STF files based on configuration
- **Database Integration**: Records STF and TF metadata in swf-monitor PostgreSQL database
- **Message Broadcasting**: Distributes TF file notifications via ActiveMQ to clients
- **Dual Operation Modes**: 
  - **Message-driven mode**: Responds to data_ready messages from swf-data-agent
  - **Continuous mode**: Periodically scans directories (for development/testing)
- **Status Reporting**: Provides health checks and performance metrics via BaseAgent

### Fast Monitoring Client 
- **Real-time Display**: Receives and displays TF file notifications in terminal
- **Statistics Tracking**: Monitors per-run TF counts and data volume
- **Graceful Shutdown**: Handles Ctrl+C with summary statistics
- **Configurable Connection**: Supports SSL and custom ActiveMQ settings

### Data Flow
1. **STF File Detection**: Agent monitors directories for new STF files or receives data_ready messages
2. **TF Simulation**: Generates TF subsamples from STF files based on configuration parameters
3. **Database Recording**: Records both STF and TF metadata in swf-monitor database via REST API
4. **Client Notification**: Broadcasts TF file notifications to `/topic/fastmon_client` 
5. **Real-time Display**: Client receives notifications and displays formatted TF information
6. **Historical Access**: All data accessible via swf-monitor Django web application

## Development and Testing

### Testing within Ecosystem
```bash
# Run all testbed tests (includes fast monitoring agent)
cd $SWF_PARENT_DIR/swf-testbed
./run_all_tests.sh

# Test agent integration specifically
cd ../swf-fastmon-agent
python -m pytest src/swf_fastmon_agent/tests/


# Check agent status in testbed
swf-testbed status
```

### Code Quality
```bash
# Format and lint (from swf-fastmon-agent directory)
black .
flake8 .
```

## Development Guidelines

This library follows the ePIC streaming workflow testbed development guidelines for portability, maintainability, and consistency across the ecosystem. See `CLAUDE.md` for detailed development guidelines and project-specific conventions.