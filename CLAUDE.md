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

## AI Development Guidelines

**Note to AI Assistant:** The following guidelines ensure consistent, high-quality contributions aligned with the ePIC streaming workflow testbed project standards.

(Taken from the `swf-testbed` README)

### General Guidelines

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