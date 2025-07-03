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

The project has been converted to Django framework with modern packaging:
```
src/swf_fastmon_agent/
├── __init__.py          # Package initialization
├── agents/              # Agent implementations
│   ├── __init__.py
│   ├── file_monitor.py  # File monitoring agent
│   └── supervisord_example.conf  # Supervisord configuration example
└── database/            # Django app for database management
    ├── __init__.py
    ├── apps.py          # Django app configuration
    ├── database.py      # Database utilities and operations
    ├── models.py        # Django ORM models (with docstrings)
    ├── settings.py      # Django settings configuration
    ├── migrations/      # Database migrations
    │   ├── 0001_initial.py
    │   ├── 0002_alter_stffile_status.py
    │   └── __init__.py
    └── tests/           # Test suite
        ├── __init__.py
        └── test_database.py
```

Additional project files:
```
├── manage.py            # Django management script
├── requirements.txt     # Python dependencies
├── pyproject.toml       # Modern Python packaging configuration
└── setup_db.py         # Database setup utility
```

### Core Library Components

- **`models.py`**: Django ORM models implementing the database schema:
  - `Run` - Data-taking run information with auto-incrementing ID
  - `StfFile` - Super Time Frame file metadata with UUID primary key
  - `Subscriber` - Message queue subscribers with fraction-based dispatch
  - `MessageQueueDispatch` - Message dispatch logging with success tracking
  - `FileStatus` - Django TextChoices enum for file processing status

- **`database.py`**: Database utilities and operations layer (implementation details TBD)
- **`settings.py`**: Django configuration for the database app
- **`manage.py`**: Django's command-line utility for administrative tasks

### Agent Components

- **`agents/file_monitor.py`**: File monitoring agent that:
  - Monitors specified directories for newly created STF files
  - Applies time-based filtering (files created within X minutes)
  - Randomly selects a configurable fraction of discovered files
  - Records selected files in the database with metadata
  - Designed for continuous operation under supervisord
  - Supports environment variable configuration for deployment flexibility

## Dependencies and External Systems

This project integrates with:
- **PostgreSQL**: Database operations using Django ORM (credentials in `.pgpass`, logs excluded)
- **ActiveMQ**: Message queuing system (logs and kahadb excluded)
- **Agent framework**: Secrets/credentials managed through `secrets.yaml`, `credentials.json`, `config.ini`

### Python Dependencies
- **Django**: Web framework with ORM for database operations (>=4.2, <5.0)
- **psycopg**: Modern PostgreSQL adapter for Python (>=3.2.0)
- **psycopg2-binary**: Legacy PostgreSQL adapter for Python (>=2.9.0)
- **pytest**: Testing framework (>=7.0.0)
- **pytest-django**: Django testing integration (>=4.5.0)
- **black**: Code formatter (>=22.0.0)
- **flake8**: Code linter (>=4.0.0)

### Database Environment Variables
Django settings support standard environment variables:
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

With Django framework in place, use these standard commands:

### Django Management
- `python manage.py runserver` - Start development server
- `python manage.py makemigrations` - Create database migrations
- `python manage.py migrate` - Apply database migrations
- `python manage.py shell` - Django interactive shell
- `python manage.py dbshell` - Database shell

### Testing and Code Quality
- `python manage.py test` - Run Django tests
- `python manage.py test swf_fastmon_agent` - Run specific app tests
- `pytest` - Run tests (alternative with pytest-django)
- `black .` - Format code
- `flake8 .` - Lint code

### Database Setup
- `python setup_db.py` - Custom database setup utility

### Agent Operations
- `python -m swf_fastmon_agent.agents.file_monitor` - Run file monitoring agent
- Configure via environment variables:
  - `FASTMON_WATCH_DIRS` - Comma-separated directories to monitor
  - `FASTMON_FRACTION` - Fraction of files to select (0.0-1.0)
  - `FASTMON_INTERVAL` - Check interval in seconds
  - `FASTMON_LOOKBACK` - Lookback time in minutes
- Use `src/swf_fastmon_agent/agents/supervisord_example.conf` for supervisord deployment

## Related Projects

This agent is part of a multi-module scientific workflow system. Dependencies on `swf-testbed`, `swf-monitor`, and `swf-daqsim-agent` suggest coordination with other components in the ecosystem.

## AI Development Guidelines

**Note to AI Assistant:** The following guidelines ensure consistent, high-quality contributions aligned with the ePIC streaming workflow testbed project standards.

(Taken from the `swf-testbed` README)

### General Guidelines

- **Do not delete anything added by a human without explicit approval!!**
- **Adhere to established standards and conventions.** When implementing new features, prioritize the use of established standards, conventions, and naming schemes provided by the programming language, frameworks, or widely-used libraries. Avoid introducing custom terminology or patterns when a standard equivalent exists.
- **Portability is paramount.** All code must work across different platforms (macOS, Linux, Windows), Python installations (system, homebrew, pyenv, etc.), and deployment environments (Docker, local, cloud). Never hardcode absolute paths, assume specific installation directories, or rely on system-specific process names or command locations. Use relative paths, environment variables, and standard tools rather than platform-specific process detection. When in doubt, choose the more portable solution.
- **Favor Simplicity and Maintainability.** Strive for clean, simple, and maintainable solutions. When faced with multiple implementation options, recommend the one that is easiest to understand, modify, and debug. Avoid overly complex or clever code that might be difficult for others (or your future self) to comprehend. Adhere to the principle of "Keep It Simple, Stupid" (KISS).
- **Follow Markdown Linting Rules.** Ensure all markdown content adheres to the project's linting rules. This includes, but is not limited to, line length, list formatting, and spacing. Consistent formatting improves readability and maintainability.
- **Maintain the prompts.** Proactively suggest additions or modifications to these tips as the project evolves and new collaboration patterns emerge.

### Project-Specific Guidelines

- **Context Refresh.** To regain context on the SWF Testbed project, follow these steps:
  1. Review the high-level goals and architecture in `swf-testbed/README.md` and `swf-testbed/docs/architecture_and_design_choices.md`.
  2. Examine the dependencies and structure by checking the `pyproject.toml` and `requirements.txt` files in each sub-project (`swf-testbed`, `swf-monitor`, `swf-common-lib`).
  3. Use file and code exploration tools to investigate the existing codebase relevant to the current task. For data models, check `models.py`; for APIs, check `urls.py` and `views.py`.
  4. Consult the conversation summary to understand recent changes and immediate task objectives.

- **Verify and Propose Names.** Before implementing new names for variables, functions, classes, context keys, or other identifiers, first check for consistency with existing names across the relevant context. Once verified, propose them for review. This practice ensures clarity and reduces rework.

### Testing Guidelines

**Ensuring Robust and Future-Proof Tests:**

- Write tests that assert on outcomes, structure, and status codes—not on exact output strings or UI text, unless absolutely required for correctness.
- For CLI and UI tests, check for valid output structure (e.g., presence of HTML tags, table rows, or any output) rather than specific phrases or case.
- For API and backend logic, assert on status codes, database state, and required keys/fields, not on full response text.
- This approach ensures your tests are resilient to minor UI or output changes, reducing maintenance and avoiding false failures.
- Always run tests using the provided scripts (`./run_tests.sh` or `./run_all_tests.sh`) to guarantee the correct environment and configuration.