# SWF Fast Monitoring Agent

**`swf-fastmon-agent`** is a fast monitoring service for the ePIC streaming workflow testbed. 

It pulls metadata of Time Frames (TF) and distribute the information via message queues, allowing remote monitoring of the 
ePIC data acquisition.

## Architecture Overview

The agent is designed to distribute metadata with and ActiveMQ messaging systems, bookkeeping activity with the swf-monitor
PostgreSQL database.


-------------- 

## Quick Start with Docker

### Prerequisites
- Docker and Docker Compose
- Python 3.9+

### 1. Start PostgreSQL Database
```bash
# Start the PostgreSQL container
docker-compose up -d

# Check container status
docker-compose ps
```

### 2. Set Up Environment (Optional)
```bash
# Copy environment template (defaults work for Docker setup)
cp .env.example .env
```

### 3. Install Dependencies
```bash
# Install Python dependencies
pip install -r requirements.txt
```

### 4. Initialize Database Schema
```bash
python manage.py runserver

# Create and apply Django migrations
python manage.py makemigrations
python manage.py migrate

# Or use the custom setup script
python setup_db.py
```

### 5. Use the Django Models
```python
import django
import os

# Configure Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'swf_fastmon_agent.database.settings')
django.setup()

from swf_fastmon_agent.database.models import Run, StfFile, FileStatus

# Create a run
run = Run.objects.create(
    run_number=1001,
    start_time="2024-01-15T10:00:00Z",
    run_conditions={"beam_energy": "18GeV", "detector": "ePIC"}
)

# Create STF file metadata
stf_file = StfFile.objects.create(
    run=run,
    machine_state="physics",
    file_url="https://example.com/stf/file123.root",
    file_size_bytes=1024000,
    checksum="abc123def456",
    status=FileStatus.REGISTERED,
    metadata={"detector": "ePIC", "beam_energy": "18GeV"}
)

# Retrieve file metadata
files = StfFile.objects.filter(run=run)
print(f"Found {files.count()} files for run {run.run_number}")
```

## Database Management

### Starting/Stopping the Database
```bash
# Start database
docker-compose up -d

# Stop database
docker-compose down

# Stop and remove data (WARNING: deletes all data)
docker-compose down -v
```

### Accessing the Database
```bash
# Connect to PostgreSQL container
docker-compose exec postgres psql -U postgres -d swf_fastmonitoring

# Or connect from host (when container is running)
psql -h localhost -U postgres -d swf_fastmonitoring
```

## Configuration

The library uses environment variables for database configuration:

- `POSTGRES_HOST` (default: localhost)
- `POSTGRES_PORT` (default: 5432)
- `POSTGRES_DB` (default: swf_fastmonitoring)
- `POSTGRES_USER` (default: postgres)
- `POSTGRES_PASSWORD` (default: postgres)

## Library Components

- **Django Models**: Core data models for the monitoring system
  - `Run`: Data-taking run information with auto-incrementing ID
  - `StfFile`: Super Time Frame file metadata with UUID primary key
  - `Subscriber`: Message queue subscribers with fraction-based dispatch
  - `MessageQueueDispatch`: Message dispatch logging with success tracking
  - `FileStatus`: Django TextChoices enum for file processing status
- **Django Management**: Standard Django commands for database operations
- **Database Utilities**: Custom database setup and operations (in `database.py`)

## Development Commands

### Django Management
```bash
python manage.py runserver      # Start development server
python manage.py makemigrations # Create database migrations
python manage.py migrate        # Apply database migrations
python manage.py shell          # Django interactive shell
python manage.py dbshell        # Database shell
```

### Testing and Code Quality
```bash
pytest          # Run tests
black .         # Format code
flake8 .        # Lint code
```

## Development Guidelines

This library follows the ePIC streaming workflow testbed development guidelines for portability, maintainability, and consistency across the ecosystem. See `CLAUDE.md` for detailed development guidelines and project-specific conventions.