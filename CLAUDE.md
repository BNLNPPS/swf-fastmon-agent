# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python-based fast monitoring agent (`swf-fastmon-agent`) that appears to be part of a larger ePIC streaming workflow testbed ecosystem, including related modules:
- `swf-testbed` - Testing environment
- `swf-monitor` - Monitoring system
- `swf-daqsim-agent` - Data acquisition simulation agent

The project is designed to work with PostgreSQL databases and ActiveMQ messaging systems.

## Development Environment

- **Python Version**: 3.9
- **IDE**: PyCharm (with Black formatter configured)
- **Code Formatter**: Black
- **License**: Apache 2.0

## Project Structure

The main source code is located in:
```
src/swf_fastmon_agent/
├── __init__.py          # Package initialization
├── models.py            # SQLAlchemy database models
└── database.py          # Database connection and operations
```

### Core Library Components

- **`models.py`**: SQLAlchemy ORM models implementing the database schema:
  - `Run` - Data-taking run information
  - `StfFile` - Super Time Frame file metadata
  - `Subscriber` - Message queue subscribers
  - `MessageQueueDispatch` - Message dispatch logging
  - `FileStatus` - Enum for file processing status

- **`database.py`**: Database management layer:
  - `DatabaseManager` class with connection pooling
  - Methods for inserting and reading STF file metadata
  - Context manager for safe database sessions
  - Environment-based configuration support

## Dependencies and External Systems

This project integrates with:
- **PostgreSQL**: Database operations using SQLAlchemy ORM (credentials in `.pgpass`, logs excluded)
- **ActiveMQ**: Message queuing system (logs and kahadb excluded)
- **Agent framework**: Secrets/credentials managed through `secrets.yaml`, `credentials.json`, `config.ini`

### Python Dependencies
- **SQLAlchemy**: ORM for database operations
- **psycopg2** (implied): PostgreSQL adapter for Python

### Database Environment Variables
The `DatabaseManager` supports the following environment variables:
- `POSTGRES_HOST` (default: localhost)
- `POSTGRES_PORT` (default: 5432)
- `POSTGRES_DB` (default: epic_monitoring)
- `POSTGRES_USER` (default: postgres)
- `POSTGRES_PASSWORD` (default: empty)

## Security Notes

- Configuration files containing secrets are gitignored: `secrets.yaml`, `credentials.json`, `config.ini`, `*.session`
- Database credentials (`.pgpass`) are excluded from version control
- Log files are excluded from commits

## Development Commands

Since this is an early-stage project with no package configuration files yet, standard Python development commands will need to be established once the project structure is implemented.

## Related Projects

This agent is part of a multi-module scientific workflow system. Dependencies on `swf-testbed`, `swf-monitor`, and `swf-daqsim-agent` suggest coordination with other components in the ecosystem.