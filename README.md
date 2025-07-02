# SWF Fast Monitoring Agent

A Django-based Python library for PostgreSQL communication and STF (Super Time Frame) file metadata management as part of the ePIC streaming workflow testbed ecosystem.

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

### 3. Initialize Database Schema
```bash
# Install dependencies (if not already done)
pip install django psycopg2-binary

# Create database tables using Django migrations
python setup_db.py
```

### 4. Use the Library
```python
from swf_fastmon_agent import DatabaseManager, FileStatus

# Create database manager (uses environment variables)
db = DatabaseManager()

# Insert STF file metadata
file_id = db.insert_stf_file(
    run_id=1,
    machine_state="physics",
    file_url="https://example.com/stf/file123.root",
    file_size_bytes=1024000,
    checksum="abc123def456",
    metadata={"detector": "ePIC", "beam_energy": "18GeV"}
)

# Retrieve file metadata
metadata = db.get_stf_file_metadata(file_id)
print(metadata)
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

- **`DatabaseManager`**: Main class for database operations using Django ORM
- **Django Models**: `Run`, `StfFile`, `Subscriber`, `MessageQueueDispatch`
- **`FileStatus` Choices**: File processing status tracking using Django TextChoices

## Development

This library follows the ePIC streaming workflow testbed development guidelines for portability, maintainability, and consistency across the ecosystem.