# SWF Fast Monitoring Agent

**`swf-fastmon-agent`** is a fast monitoring service for the ePIC streaming workflow testbed. 

This agent pulls metadata of Time Frames (TF) and distributes the information via ActiveMQ message queues, enabling real-time remote monitoring of ePIC data acquisition processes.

## Architecture Overview

The fast monitoring agent is designed as part of the **SWF testbed ecosystem** and integrates with:
- **swf-monitor**: PostgreSQL database and Django web interface for persistent monitoring data
- **swf-testbed**: Infrastructure orchestration and process management
- **swf-data-agent**: Receiving messages when STF files are available for fast monitoring

The agent operates as a managed service within the swf-testbed ecosystem, automatically configured and monitored through the central CLI.

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

# Manual development run (for testing)
cd ../swf-fastmon-agent
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

- **Metadata Extraction**: Pulls Time Frame metadata from data acquisition systems
- **Message Publishing**: Distributes metadata via ActiveMQ to registered subscribers
- **Database Integration**: Stores monitoring data in swf-monitor PostgreSQL database
- **Subscriber Management**: Handles subscription requests and message routing
- **Status Reporting**: Provides health checks and performance metrics

### Data Flow
1. **Data Acquisition**: Monitors ePIC DAQ systems for new Time Frame files
2. **Metadata Processing**: Extracts file metadata, checksums, and run conditions
3. **Message Distribution**: Publishes to ActiveMQ topics for real-time monitoring
4. **Database Storage**: Persists metadata in swf-monitor for historical analysis
5. **Web Interface**: Accessible via swf-monitor Django web application

## Development and Testing

### Testing within Ecosystem
```bash
# Run all testbed tests (includes fast monitoring agent)
cd $SWF_PARENT_DIR/swf-testbed
./run_all_tests.sh

# Test agent integration specifically
cd ../swf-fastmon-agent
python -m pytest tests/

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